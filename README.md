# Webscraping Google Maps

Este repositório contém um script simples (`scraping.py`) que usa Selenium para pesquisar estabelecimentos no Google Maps e extrair: nome, endereço, telefone, site e descrição/categoria.

## Requisitos
- Windows 10/11
- Python 3.8+
- Google Chrome instalado (compatível com o chromedriver que será gerenciado automaticamente)

## Passos (PowerShell)

1. Verifique se o Python está instalado:

```powershell
py --version
python --version
```

2. Se não estiver instalado, instale com o `winget` (ou pelo instalador do site oficial). Na instalação GUI, marque "Add Python to PATH".

```powershell
winget install --id=Python.Python.3 -e
```

3. (Opcional) Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Instale dependências:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

5. Se estiver tendo problemas com o comando `python` apontando para a Microsoft Store, desative os "App execution aliases":

- Abra Configurações > Aplicativos > Execução de aplicativos (App execution aliases)
- Desative `python.exe` e `python3.exe` apontando para a Store.

6. Execute o script:

```powershell
python d:\Webscraping\scraping.py
```

## Notas
- O script usa `webdriver-manager` para baixar o chromedriver automaticamente. Garanta que o Chrome esteja instalado e atualizado.
- Se quiser rodar sem abrir o navegador, descomente a opção `chrome_options.add_argument('--headless=new')` em `scraping.py`.
- Erros comuns:
  - `ModuleNotFoundError`: instale as dependências com `pip install -r requirements.txt`.
  - Problemas com driver: atualize o `selenium` e `webdriver-manager`.

## Saída
O script imprime no terminal os campos: name, address, phone, site e description para cada estabelecimento encontrado.

Se quiser, posso também adicionar suporte para salvar em CSV/JSON — diga se prefere CSV ou JSON.
