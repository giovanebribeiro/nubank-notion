# nubank-notion

Script de integração entre uma conta no Nubank e uma tabela no Notion, mais focada em finanças e controle de gastos

**IMPORTANTE**: O script está inteiramente customizado para as minhas necessidades apenas e não há interesse em torná-lo mais "genérico. A pouca parametrização que existe se refere apenas as varíaveis sensíveis. Os passos aqui são apenas educacionais e reproduzi-los é inteiramente por sua conta e risco.

## Setup

Após o clone do projeto e a execução do pipenv (para instalação de dependências), é necessário criar um arquivo json chamado 'secret.json', com a seguinte estrutura:

```json
{
	"nubank": {
		"user": "seu_cpf",
		"pass": "senha_do_app_nubank"
	},
	"notion": {
		"database_id": "id_do_database_de_transações_no_notion",
		"token": "token_de_acesso_a_api_do_notion",
		"api_version": "2022-06-28"
	}
}
```

Depois, é necessário criar um certificado para acesso a API do Nubank, seguindo as instruções [deste link](https://github.com/andreroggeri/pynubank/blob/main/examples/login-certificate.mdf).

Após estas configurações, o script pode ser executado sem problemas.