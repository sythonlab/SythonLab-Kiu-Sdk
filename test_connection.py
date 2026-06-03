from sythonlab_kiu_sdk.flights.v3.sdk import KiuFlightSDK

sdk = KiuFlightSDK(
    iso_country="JM",
    debug=True
)

status, data = sdk.check_connection(show_response=True)

print(status, data)
