



https://github.com/user-attachments/assets/be1691f9-215a-4c55-ac92-fe4ef8917f19


# Gestão Acadêmica

Sistema web de gestão acadêmica desenvolvido com Django. Permite administrar cursos, disciplinas, semestres, alunos e matrículas, além de consultar e compartilhar boletins.

## Funcionalidades

- Cadastro, edição e consulta de cursos, disciplinas e semestres.
- Cadastro e busca de alunos, com validação de RGM numérico de 7 dígitos.
- Matrículas em disciplinas da grade curricular do curso do aluno.
- Registro de notas e frequência, com situação calculada: cursando, aprovado, reprovado ou reprovado por falta.
- Boletim individual para consulta e impressão/salvamento como PDF pelo navegador.
- QR Code com link público assinado para consulta do boletim.
- Painel administrativo Django e interface com Bootstrap e HTMX.
- Comando opcional para criar dados acadêmicos de demonstração.

## Requisitos

- Windows (as instruções abaixo e o `feira.bat` são voltados a esse sistema).
- Python 3.12 ou mais recente.
- `pip`, instalado junto com o Python.

As dependências Python estão fixadas em [`requirements.txt`](requirements.txt).

## Instalação e execução local

Abra o PowerShell na pasta do projeto (a pasta que contém `requirements.txt`) e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd .\app
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra <http://127.0.0.1:8000/>. Entre com o usuário criado para acessar as páginas do sistema; o painel administrativo fica em <http://127.0.0.1:8000/admin/>.

O SQLite é criado em `app\db.sqlite3` na primeira execução das migrações. Esse arquivo é local e não é versionado pelo Git. Para preparar os dados de exemplo, opcionalmente rode, ainda na pasta `app`:

```powershell
python manage.py populate_demo_data
```

O comando adiciona cursos, disciplinas, semestres, alunos e matrículas de demonstração sem apagar registros existentes. Se for executado novamente, cria somente os registros que ainda não existem.

## Executar para uma demonstração na rede local

Na raiz do projeto, com o ambiente virtual ativado e as dependências instaladas nele, execute:

```powershell
.\feira.bat
```

O script inicia o servidor na porta `8000` e mostra os endereços de rede encontrados. Abra um deles no computador ou celular conectado à mesma rede Wi-Fi. Se o Windows perguntar, permita o acesso na rede privada. Encerre o servidor com `Ctrl+C`.

`feira.bat` é um atalho de desenvolvimento/demonstração, não um servidor de produção.

## Testes

Na pasta `app`, execute:

```powershell
python manage.py test
```

## Estrutura do projeto

```text
app/
  aluno/       Alunos, matrículas, boletins e suas migrações
  curso/       Cursos, disciplinas, semestres e dados de demonstração
  app/         Configurações e rotas principais do Django
  templates/   Templates HTML
  static/      Arquivos CSS e bibliotecas locais
  manage.py    Utilitário de gerenciamento do Django
feira.bat      Inicialização do servidor para demonstração no Windows
requirements.txt
```

## Configuração para produção

Por padrão, o projeto usa configurações de desenvolvimento. Para produção, configure as variáveis de ambiente antes de iniciar:

- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY` com uma chave secreta forte e privada.
- `DJANGO_ALLOWED_HOSTS` com os domínios permitidos, separados por vírgula.

Com `DEBUG=0`, o projeto exige uma chave secreta e hosts explicitamente configurados, habilita cookies seguros e redirecionamento HTTPS. O `runserver` do Django não deve ser usado como servidor de produção.
