import base64
from dataclasses import dataclass, field
import datetime
import hashlib
import logging
import os
from typing import Literal, Optional
import uuid

import requests

_LOGGER = logging.getLogger(__name__)


@dataclass
class Line:
    Label: str
    Usage: float
    Read: float
    IsEstimated: bool
    MeterSerialNumberHis: str


@dataclass
class MeterUsage:
    IsError: bool
    IsDataAvailable: bool
    IsConsumptionAvailable: bool
    TargetUsage: float
    AverageUsage: float
    ActualUsage: float
    MyUsage: str  # so far have only seen 'NA'
    AverageUsagePerPerson: float
    IsMO365Customer: bool
    IsMOPartialCustomer: bool
    IsMOCompleteCustomer: bool
    IsExtraMonthConsumptionMessage: bool
    Lines: list[Line] = field(default_factory=list)
    AlertsValues: Optional[dict] = field(
        default_factory=dict
    )  # assumption that it could be a dict


@dataclass
class Measurement:
    hour_start: datetime.datetime
    usage: int  # Usage
    total: int  # Read


class ThamesWater:
    def __init__(
        self,
        email: str,
        password: str,
        account_number: int,
        client_id: str = "cedfde2d-79a7-44fd-9833-cae769640d3d",  # specific to Thames Water
    ):
        self.s = requests.session()
        self.account_number = account_number
        self.client_id = client_id
        self.email = email
        
        # Set default headers that should be present in all requests
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1"
        })

        self._authenticate(email, password)

    def _generate_pkce(self):
        self.pkce_verifier = (
            base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
        )
        self.pkce_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(self.pkce_verifier.encode()).digest()
            )
            .decode("utf-8")
            .rstrip("=")
        )

    def _authorize_b2c_1_tw_website_signin(self) -> tuple[str, str]:
        url = "https://login.thameswater.co.uk/identity.thameswater.co.uk/b2c_1_tw_website_signin/oauth2/v2.0/authorize"

        # Store these for later use
        self.state = str(uuid.uuid4())
        self.nonce = str(uuid.uuid4())

        params = {
            "client_id": self.client_id,
            "scope": "openid profile offline_access",
            "response_type": "code",
            "redirect_uri": "https://www.thameswater.co.uk/login",
            "response_mode": "fragment",
            "code_challenge": self.pkce_challenge,
            "code_challenge_method": "S256",
            "nonce": self.nonce,
            "state": self.state,
        }

        headers = {
            "Origin": "https://www.thameswater.co.uk",
            "Referer": "https://www.thameswater.co.uk/",
        }
        
        r = self.s.get(url, params=params, headers=headers)
        r.raise_for_status()
        
        cookies = dict(self.s.cookies)
        if "x-ms-cpim-trans" not in cookies or "x-ms-cpim-csrf" not in cookies:
            raise Exception("Failed to get authentication tokens from cookies")
            
        return cookies["x-ms-cpim-trans"], cookies["x-ms-cpim-csrf"]

    def _self_asserted_b2c_1_tw_website_signin(
        self, email: str, password: str, trans_token: str, csrf_token: str
    ):
        url = "https://login.thameswater.co.uk/identity.thameswater.co.uk/B2C_1_tw_website_signin/SelfAsserted"

        params = {
            "tx": f"StateProperties={trans_token}",
            "p": "B2C_1_tw_website_signin",
        }

        data = {"request_type": "RESPONSE", "email": email, "password": password}

        headers = {
            "Origin": "https://login.thameswater.co.uk",
            "Referer": f"https://login.thameswater.co.uk/identity.thameswater.co.uk/b2c_1_tw_website_signin/oauth2/v2.0/authorize?client_id={self.client_id}",
            "x-csrf-token": csrf_token,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        r = self.s.post(url, params=params, data=data, headers=headers)
        r.raise_for_status()
        
        # Verify the response
        if r.status_code != 200:
            _LOGGER.error("Self-asserted signin failed with status %d", r.status_code)
            _LOGGER.debug("Response content: %s", r.text)
            raise Exception("Authentication failed")

    def _confirmed_b2c_1_tw_website_signin(self, trans_token: str, csrf_token: str):
        url = "https://login.thameswater.co.uk/identity.thameswater.co.uk/B2C_1_tw_website_signin/api/CombinedSigninAndSignup/confirmed"

        headers = {
            "Origin": "https://login.thameswater.co.uk",
            "Referer": f"https://login.thameswater.co.uk/identity.thameswater.co.uk/b2c_1_tw_website_signin/unified?csrf_token={csrf_token}&tx=StateProperties%3D{trans_token}",
            "Accept": "text/html,application/json",
            "X-Requested-With": "XMLHttpRequest"
        }

        params = {
            "rememberMe": "false",
            "tx": f"StateProperties={trans_token}",
            "csrf_token": csrf_token,
            "p": "B2C_1_tw_website_signin",
        }

        r = self.s.get(url, headers=headers, params=params)
        r.raise_for_status()

        try:
            # The response URL contains the code in the fragment
            fragment = r.url.split("#")[1]
            params = dict(param.split('=') for param in fragment.split('&'))
            
            if 'error' in params:
                raise Exception(f"Authentication error: {params.get('error_description', 'Unknown error')}")
                
            if 'code' not in params:
                raise Exception("No authorization code in response")
                
            return params['code']
        except Exception as e:
            _LOGGER.error("Failed to parse confirmation response: %s", str(e))
            _LOGGER.debug("Response URL: %s", r.url)
            raise

    def _get_oauth2_code_b2c_1_tw_website_signin(self, confirmation_code: str):
        url = "https://login.thameswater.co.uk/identity.thameswater.co.uk/b2c_1_tw_website_signin/oauth2/v2.0/token"

        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=utf-8",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        }

        data = {
            "client_id": self.client_id,
            "redirect_uri": "https://www.thameswater.co.uk/login",
            "scope": "openid offline_access profile",
            "grant_type": "authorization_code",
            "client_info": "1",
            "x-client-SKU": "msal.js.browser",
            "x-client-VER": "3.1.0",
            "x-ms-lib-capability": "retry-after, h429",
            "x-client-current-telemetry": "5|865,0,,,|,",
            "x-client-last-telemetry": "5|0|||0,0",
            "code_verifier": self.pkce_verifier,
            "code": confirmation_code,
        }

        r = self.s.post(url, headers=headers, data=data)
        r.raise_for_status()
        self.oauth_request_tokens = r.json()

    def _refresh_oauth2_token_b2c_1_tw_website_signin(self):
        url = "https://login.thameswater.co.uk/identity.thameswater.co.uk/b2c_1_tw_website_signin/oauth2/v2.0/token"

        data = {
            "client_id": self.client_id,
            "scope": "openid profile offline_access",
            "grant_type": "refresh_token",
            "client_info": "1",
            "x-client-SKU": "msal.js.browser",
            "x-client-VER": "3.1.0",
            "x-ms-lib-capability": "retry-after, h429",
            "x-client-current-telemetry": "5|61,0,,,|@azure/msal-react,2.0.3",
            "x-client-last-telemetry": "5|0|||0,0",
            "refresh_token": self.oauth_request_tokens["refresh_token"],
        }

        headers = {"content-type": "application/x-www-form-urlencoded;charset=utf-8"}

        r = self.s.get(url, headers=headers, data=data)
        r.raise_for_status()
        self.oauth_response_tokens = r.json()

    def _login(self, state: str, id_token: str):
        url = "https://myaccount.thameswater.co.uk/login"

        data = {
            "state": state,
            "id_token": id_token,
        }

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
            "content-type": "application/x-www-form-urlencoded",
        }

        r = self.s.post(url, data=data, headers=headers)
        r.raise_for_status()

    def _authenticate(
        self,
        email: str,
        password: str,
    ):
        _LOGGER.debug("Starting authentication process for email: %s", email)
        self._generate_pkce()
        _LOGGER.debug("Generated PKCE challenge: %s", self.pkce_challenge)
        
        trans_token, csrf_token = self._authorize_b2c_1_tw_website_signin()
        _LOGGER.debug("Got authorization tokens - trans: %s, csrf: %s", trans_token, csrf_token)
        
        self._self_asserted_b2c_1_tw_website_signin(
            email, password, trans_token, csrf_token
        )
        _LOGGER.debug("Self-asserted authentication completed")
        
        confirmation_code = self._confirmed_b2c_1_tw_website_signin(
            trans_token, csrf_token
        )
        _LOGGER.debug("Got confirmation code")
        
        self._get_oauth2_code_b2c_1_tw_website_signin(confirmation_code)
        _LOGGER.debug("OAuth2 code obtained")
        
        self._refresh_oauth2_token_b2c_1_tw_website_signin()
        _LOGGER.debug("OAuth2 token refreshed")

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
            "Referer": f"https://myaccount.thameswater.co.uk/twservice/Account/SignIn?useremail=igor.malin.uk@gmail.com",
        }

        r = self.s.get("https://myaccount.thameswater.co.uk/mydashboard")
        r = self.s.get(
            f"https://myaccount.thameswater.co.uk/mydashboard/my-meters-usage?contractAccountNumber={self.account_number}"
        )
        r = self.s.get(
            "https://myaccount.thameswater.co.uk/twservice/Account/SignIn?useremail=",
            headers=headers,
        )
        state = r.url.split("&state=")[1].split("&nonce=")[0].replace("%3d", "=")
        id_token = r.text.split("id='id_token' value='")[1].split("'/>")[0]
        self.s.get(r.url)
        self._login(state, id_token)
        self.s.cookies.set(name="b2cAuthenticated", value="true")

    def get_meter_usage(
        self,
        meter: int,
        start: datetime.datetime,
        end: datetime.datetime,
        granularity: Literal["H", "D", "M"] = "H",
    ) -> MeterUsage:
        _LOGGER.debug(
            "Getting meter usage for meter %s from %s to %s with granularity %s",
            meter,
            start.isoformat(),
            end.isoformat(),
            granularity,
        )
        url = "https://myaccount.thameswater.co.uk/ajax/waterMeter/getSmartWaterMeterConsumptions"

        params = {
            "meter": meter,
            "startDate": start.day,
            "startMonth": start.month,
            "startYear": start.year,
            "endDate": end.day,
            "endMonth": end.month,
            "endYear": end.year,
            "granularity": granularity,
            "premiseId": "",
            "isForC4C": "false",
        }
        _LOGGER.debug("Request parameters: %s", params)

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
            "Referer": "https://myaccount.thameswater.co.uk/mydashboard/my-meters-usage?contractAccountNumber=900083321375",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            r = self.s.get(url, params=params, headers=headers)
            r.raise_for_status()
            _LOGGER.debug("Response status code: %s", r.status_code)
            
            data = r.json()
            _LOGGER.debug("Raw response data: %s", data)
            
            data["Lines"] = [Line(**line) for line in data["Lines"]]
            meter_usage = MeterUsage(**data)
            _LOGGER.debug("Processed meter usage: %s", meter_usage)
            return meter_usage
        except Exception as e:
            _LOGGER.error("Error getting meter usage: %s", str(e))
            raise
