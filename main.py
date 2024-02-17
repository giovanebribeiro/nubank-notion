import json, datetime
import logging
import logging.handlers
import requests
from datetime import timedelta, datetime

from pynubank import Nubank

LOG_LEVEL=logging.DEBUG

categories = {
	"sa\u00fade": "b01e7b9fb16640ca8fabf1b58a6b7501", 					# categoria 'saúde'
	"servi\u00e7os": "e8a3abea79b440cfb09422e978e298f1", 				# categoria 'serviços'
	"outros": "fcb23f373c28469aac558525f7fccf9d", 						# categoria 'livre'
	"supermercado": "4faadd6e4c8844d1a1fd4913ead4c4dc",					# categoria 'mercado'
	"transporte": "606ba1a2ef084b0b84c8e19211acbf59",					# categoria 'transporte'
	"educa\u00e7\u00e3o": "89ff010acbfe4fc1930049c130691bf8" 			# categoria 'educação'
}

log = logging.getLogger("nubank-notion")

syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
log.addHandler(syslog_handler)
stream_handler = logging.StreamHandler()
log.addHandler(stream_handler)

log.setLevel(LOG_LEVEL)

log.debug("Carregando arquivo de variáveis sensíveis")
with open('./secret.json', 'r') as s:
	creds = json.loads(s.read())
	s.close()


log.debug("Carregando variáveis referentes ao Notion")
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

def transactions_filter(d):
	t = d.get("time") 
	try:
		t = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
	except ValueError:
		t = datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ")


	if t > (datetime.now() - timedelta(days=1)):
		return d
	else:
		pass

def save_transaction(t, tt=None, ta=None, charge=1, total_charges=1):

	if tt is None:
		tt = t.get("time")

	if ta is None:
		ta = t.get("amount")

	desc = t.get("description")
	if total_charges > 1:
		desc = f"{desc} ({charge}/{total_charges})"

	data = {
		"parent": {
			"database_id": notion_database
		},
		"properties": {
			"Name": {
				"title": [
					{
						"text": {
							"content": desc
						}
					}
				]
			},
			"Date": {
				"date": {
					"start": tt
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
				"number": (ta/100)
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
		log.info(f"Transação adicionada com sucesso: {resp_id}")
	else:
		log.error(f"Algum erro aconteceu... {resp.text}")

nu = Nubank()
nu_creds = creds.get("nubank")
nu.authenticate_with_cert(nu_creds.get('user'), nu_creds.get('pass'), './cert.p12')
card_statements = nu.get_card_statements()

for t in card_statements:
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

	if len(response.get("results")) > 0:
		log.warning("Transação encontrada! Nada a fazer...")
		break

	log.warning("Transação não encontrada. Adicionando ao Notion")
	log.debug(json.dumps(t))

	log.debug("Verificando a data da transação")
	tt = t.get("time") 
	try:
		tt = datetime.strptime(tt, "%Y-%m-%dT%H:%M:%SZ")
	except ValueError:
		tt = datetime.strptime(tt, "%Y-%m-%dT%H:%M:%S.%fZ")
	
	if tt.day > 28: # se a data da compra for após o vencimento da fatura, coloque-a no próximo mês
		next_month = tt.month + 1
		tt = datetime(year=tt.year, month=next_month, day=1)

	log.debug("Verificando as parcelas")
	t_details = t.get("details")
	
	charges = t_details.get("charges")
	if charges is None: # parcela única
		log.debug("Transação não possui parcelas. ")
		tt = tt.strftime("%Y-%m-%dT%H:%M:%SZ")
		save_transaction(t, tt=tt)
	else:
		log.debug(f"Transação possui parcelas: {charges} ")
		total_charges = charges.get("count")
		for c in range(0, total_charges):
			ta = charges.get("ammount")

			new_tt = tt
			if total_charges > 1 and c > 0:
				next_days = 30*c
				new_tt = tt + timedelta(days=next_days)

		
			transaction_time = new_tt.strftime("%Y-%m-%dT%H:%M:%SZ")
			save_transaction(t=t, tt=transaction_time, ta=ta, charge=(c+1), total_charges=total_charges)

	log.info("========================")
