import requests
import xml.etree.ElementTree as ET

url = "https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx"
headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": "http://tempuri.org/GetHatOtoKonum_json"
}

# Replace 129T with any valid route code
soap_body = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetHatOtoKonum_json xmlns="http://tempuri.org/">
      <HatKodu>79KM</HatKodu>
    </GetHatOtoKonum_json>
  </soap:Body>
</soap:Envelope>
"""

response = requests.post(url, headers=headers, data=soap_body)
# print(response.text)
root = ET.fromstring(response.content)
ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
body = root.find('soap:Body', ns)
result = body.find('.//{http://tempuri.org/}GetHatOtoKonum_jsonResponse/{http://tempuri.org/}GetHatOtoKonum_jsonResult')
import json
data = json.loads(result.text)
print(data)