import json, datetime

import requests

from datetime import timedelta, datetime

from pynubank import Nubank

nu = Nubank()

with open('./secret.json', 'r') as s:
	creds = json.loads(s.read())
	s.close()

nu_creds = creds.get("nubank")

nu.authenticate_with_cert(nu_creds.get('user'), nu_creds.get('pass'), './cert.p12')

card_statements = nu.get_card_statements()
def comp(d):
	t = d.get("time") 
	try:
		t = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
	except ValueError:
		t = datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ")


	if t > (datetime.now() - timedelta(days=1)):
		return d
	else:
		pass

today_transactions = list(filter(comp, card_statements))

notion_creds = creds.get("notion")
notion_token = notion_creds.get("token")
notion_database = notion_creds.get("database_id")

notion_headers = {
 	"Accept": "*/*",
 	"Content-Type": "application/json",
 	"Notion-Version": notion_creds.get("api_version"),
 	"Authorization": f"Bearer {notion_token}"
}

notion_url = f"https://api.notion.com/v1"

categories = {
	"sa\u00fade": "b01e7b9fb16640ca8fabf1b58a6b7501",
	"servi\u00e7os": "e8a3abea79b440cfb09422e978e298f1",
	"outros": "fcb23f373c28469aac558525f7fccf9d" # página (livre)
}

for t in today_transactions:

	# query if transaction exists
	payload = json.dumps({
		"filter": {
			"property": "bank_id_transaction",
			"rich_text": {
				"equals": t.get("id")
			}
		}
	})
	resp = requests.request("POST", f"{notion_url}/databases/{notion_database}/query", data=payload,  headers=notion_headers)
	response = resp.json()

	if len(response.get("results")) == 0:
		print("Transação não encontrada. Adicionando ao Notion")

		data = {
			"parent": {
				"database_id": notion_database
			},
			"properties": {
				"Name": {
					"title": [
						{
							"text": {
								"content": t.get("description")
							}
						}
					]
				},
				"Date": {
					"date": {
						"start": t.get("time")
					}
				},
				"bank_id_transaction": {
					"rich_text": [
						{
							"text": {
								"content": t.get("id")
							}
						}
					]
				},
				"Value": {
					"number": (t.get("amount")/100)
				},
				"🏦 Origem": {
					"relation": [
						{
							"id": "ca9e409f96534a4dbc81ae11fca38b35" # página NuCartão
						}
					]
				}
			}
		}
		
		t_category = t.get("title")
		page_id = categories.get(t_category)
		if page_id is not None:
			data.get("properties").update({
				"✉️ Categoria": {
					"relation": [
						{
							"id": page_id
						}
					]
				}
			})


		payload = json.dumps(data)
	
		resp = requests.request("POST", f"{notion_url}/pages", data=payload,  headers=notion_headers)
		status_code = resp.status_code
		if status_code == 200:
			resp_id = resp.json().get("id")
			print(f"Transação adicionada com sucesso: {resp_id}")
		else:
			print(f"Algum erro aconteceu... {resp.text}")
			
	else:
		print("Transação encontrada! Nada a fazer...")








	#print(json.dumps(t))
	#print(t.get("amount"))
	#print(t.get("id"))
	print("========================")
