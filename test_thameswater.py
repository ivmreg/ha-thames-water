import datetime
import logging
import sys
from custom_components.thames_water.thameswaterclient import ThamesWater

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Your credentials
EMAIL = "igor.malin.uk@gmail.com"
PASSWORD = "@1nk0gn1T01"
ACCOUNT_NUMBER = 900083321375  # Your Thames Water account number
METER_NUMBER = 312428674   # Your meter number

try:
    # Initialize the client
    client = ThamesWater(
        email=EMAIL,
        password=PASSWORD,
        account_number=ACCOUNT_NUMBER
    )
    
    # Get meter usage for the last 24 hours
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=1)
    
    meter_usage = client.get_meter_usage(
        meter=METER_NUMBER,
        start=start,
        end=end,
        granularity="H"
    )
    
    print("\nMeter Usage Results:")
    print(f"Target Usage: {meter_usage.TargetUsage}")
    print(f"Average Usage: {meter_usage.AverageUsage}")
    print(f"Actual Usage: {meter_usage.ActualUsage}")
    print(f"\nDetailed Lines:")
    for line in meter_usage.Lines:
        print(f"Label: {line.Label}, Usage: {line.Usage}, Read: {line.Read}, Estimated: {line.IsEstimated}")

except Exception as e:
    logging.error("Error occurred: %s", str(e), exc_info=True)