# Relatório Técnico de Melhorias — Gestão Acadêmica (django_pibic)

Este documento registra cada melhoria aplicada ao sistema: **o problema**, **por que importa**, **o que foi feito** e **como foi verificado**.

## Visão geral do sistema

Sistema web em **Django 6.1** para gestão acadêmica (Cursos, Disciplinas, Semestres e Alunos), com:
- **Class-Based Views** (`ListView`, `CreateView`, `UpdateView`, `DeleteView`) pro CRUD;
- **HTMX** pra editar e excluir em modais sem recarregar a página;
- **Jazzmin** como tema do painel administrativo;
- **SQLite** como banco de dados.

---

## Melhoria 1 — Exclusão de curso com alunos vinculados

### Problema
O modelo `Student` aponta pra `Course` com `on_delete=models.PROTECT`. Essa regra é correta, porque impede apagar um curso e deixar alunos "órfãos". Só que a exceção `ProtectedError` lançada pelo Django **não era tratada**. Na prática, ao tentar excluir um curso com alunos:
- na página normal, o usuário via um **erro 500** (tela de erro do servidor);
- no modal HTMX, a requisição falhava e o modal travava sem dar nenhum retorno.

Além disso, o texto da tela de confirmação dizia que "alunos vão junto", o que **não é verdade**: o banco bloqueia a exclusão.

### Por que importa
- **Experiência do usuário:** erro 500 passa a impressão de sistema quebrado, quando na verdade a regra de negócio funcionou.
- **Clareza:** o usuário precisa saber *por que* não conseguiu excluir e *o que fazer* pra resolver.
- **Integridade dos dados:** a proteção do banco continua valendo. Mudou só a forma de comunicar o bloqueio.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `app/htmx.py` | `HtmxModalDeleteMixin.form_valid` agora captura `ProtectedError` e devolve a própria tela de confirmação com uma mensagem de erro (contando os registros vinculados). Funciona tanto na página normal quanto no modal HTMX. Também passou a excluir **antes** de montar a resposta de sucesso, o que deixa o fluxo mais seguro. |
| `templates/partials/modal_confirm_delete.html` | Mostra um alerta amarelo com a mensagem e esconde o botão "Excluir" quando há erro. |
| `templates/confirm_delete.html` | O mesmo tratamento, mais a correção do texto enganoso ("alunos vão junto" → "Cursos com alunos não podem ser excluídos"). |
| `curso/tests.py` | Dois testes novos (`ProtectedCourseDeleteTests`): a exclusão bloqueada mostra a mensagem e o curso continua no banco, nos fluxos normal e HTMX. |

**Decisão de design:** a correção ficou no *mixin* compartilhado, e não em cada view. Assim, qualquer entidade que ganhe uma relação `PROTECT` no futuro já recebe o tratamento sem nenhum código novo.

### Verificação
- `python manage.py test` → **15 testes, todos passando**.
- Teste manual no navegador: excluir "Administração" (curso com 4 alunos) agora mostra:
  > Não é possível excluir "Administração": existem 4 registro(s) vinculado(s). Remova ou transfira esses registros antes.

---

## Melhoria 2 — Semestres duplicados ou fora da duração do curso

### Problema
O modelo `Semester` não tinha nenhuma regra sobre o campo `number`. Com isso era possível:
- cadastrar **dois "1º semestre"** pro mesmo curso;
- cadastrar o **"15º semestre"** num curso de 8 semestres;
- cadastrar o **"semestre 0"**.

### Por que importa
- **Integridade dos dados:** a grade curricular fica inconsistente, e relatórios e telas mostram semestres repetidos ou impossíveis.
- **Regra de negócio no lugar certo:** a regra fica no **modelo**, não só na tela, então vale para *qualquer* entrada de dados: formulário do site, modal HTMX e painel admin.
- **Defesa em profundidade:** a restrição de unicidade também existe **no banco de dados**. Mesmo um script ou uma importação que pule as validações do Django não consegue gravar duplicados.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `curso/models.py` | `UniqueConstraint(course, number)` com mensagem em português, mais o método `clean()` validando `1 ≤ número ≤ duração do curso`. |
| `curso/migrations/0002_semester_unique_per_course.py` | Migração que cria a restrição no banco. Antes de aplicar, confirmei que os dados existentes não tinham duplicados nem semestres inválidos. |
| `curso/tests.py` | 4 testes novos (`SemesterValidationTests`): duplicado, acima da duração, zero, e caso válido. |

**Por que não precisou mexer nas views ou nos templates:** o `ModelForm` do Django chama `full_clean()` automaticamente, e isso executa `clean()` e valida as `constraints`. Os templates já exibiam erros de campo e erros gerais. Bastou colocar a regra no modelo.

### Verificação
- `python manage.py test` → **19 testes, todos passando**.
- Teste manual: criar o semestre 15 para "Administração" mostra *"O curso Administração tem só 8 semestres."* e nada é salvo.

---

## Melhoria 3 — Validação do formato do RGM

### Problema
O campo `rgm` só limitava o tamanho (`max_length=7`), sem checar o conteúdo. Uma análise do banco mostrou que **nenhum dos 49 alunos** tinha um RGM no padrão:
- 48 alunos de demonstração com letra + 6 dígitos (`D080004`), formato criado pelo gerador `populate_demo_data`;
- 1 aluno cadastrado à mão com pontuação (`114.008`);
- enquanto isso, os testes usavam 7 dígitos (`1234567`).

Ou seja, o próprio sistema tinha três formatos diferentes pro mesmo dado.

### Por que importa
- **Padronização:** um identificador acadêmico precisa de um formato único pra busca, integração com outros sistemas e emissão de documentos.
- **Qualidade na entrada:** erros de digitação (letras, pontos, dígitos faltando) são barrados na hora, com uma mensagem clara.
- **Corrigir a origem, não só o sintoma:** além de validar, ajustei o gerador de dados e converti os dados que já existiam. Sem isso, todos os alunos atuais dariam erro ao serem editados.

### Decisão
Formato definido junto ao responsável pelo projeto: **exatamente 7 dígitos numéricos** (ex.: `0123456`).

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `aluno/models.py` | `RegexValidator(r"^\d{7}$")` no campo `rgm`, com mensagem em português. Vale no site, no modal HTMX e no admin. |
| `aluno/migrations/0002_rgm_seven_digits.py` | **Migração de dados** que converte os RGMs existentes: mantém só os dígitos e completa com zeros à esquerda (`D080004` → `0080004`, `114.008` → `0114008`). Antes de aplicar, simulei a conversão e confirmei que **não gerava duplicados** (49 RGMs → 49 únicos). |
| `curso/management/commands/populate_demo_data.py` | O gerador de demonstração passou a criar RGMs de 7 dígitos (`0100001`). |
| `aluno/tests.py` | 2 testes novos (`StudentRgmValidationTests`): 4 formatos inválidos rejeitados e 1 válido aceito. |

### Achado extra: migração desatualizada
Ao gerar a migração, o Django detectou que a `0001_initial` de `aluno` registrava `on_delete=CASCADE`, enquanto o modelo usa `PROTECT`. O comportamento real já era `PROTECT` (o Django aplica a regra pelo modelo, por isso a Melhoria 1 funcionou), mas o histórico de migrações estava inconsistente. A nova migração **alinha o histórico ao código**, e `makemigrations --check` agora não aponta nenhuma pendência.

### Verificação
- `python manage.py test` → **21 testes, todos passando**.
- Banco após a migração: **0 RGMs fora do padrão**.
- Teste manual: cadastrar um aluno com RGM `12A.456` mostra *"O RGM deve ter exatamente 7 dígitos numéricos."* e nada é salvo.

---

## Melhoria 4 — Remoção de código duplicado na edição de semestre

### Problema
O projeto já tinha um *mixin* reutilizável, `HtmxModalUpdateMixin` em `app/htmx.py`, que implementa a edição em modal para Curso, Disciplina e Aluno. A `SemesterUpdateView`, porém, **reescrevia a mesma lógica à mão**: checagem do cabeçalho HTMX, renderização do card, os cabeçalhos `HX-Retarget`/`HX-Reswap`/`HX-Trigger-After-Swap`, num total de 19 linhas.

O motivo provável: o modal de semestre usa um evento JavaScript diferente pra fechar (`semesterUpdated`), enquanto o mixin tinha o nome do evento **fixo no código** (`actionModalDone`).

### Por que importa
- **Princípio DRY (*Don't Repeat Yourself*):** duas cópias da mesma lógica precisam ser mantidas em dobro. Uma correção feita no mixin não chegaria ao semestre.
- **Consistência:** todas as telas de edição agora seguem exatamente o mesmo fluxo.
- **Menos código = menos lugar pra bug.**

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `app/htmx.py` | O nome do evento virou o atributo `modal_done_event` (padrão `actionModalDone`). As outras telas continuam iguais, sem nenhuma alteração. |
| `curso/views.py` | `SemesterUpdateView` passou a usar o mixin, só com configuração (templates, prefixo do id e `modal_done_event = "semesterUpdated"`). Os métodos `get_template_names` e `form_valid` foram apagados, junto com o import de `render`, que deixou de ser usado. |
| `curso/tests.py` | O teste existente do modal de semestre agora também confere o evento `semesterUpdated`, garantindo que o modal continua fechando. |

**Resultado:** a view ficou de 25 para 11 linhas, sem mudar nenhum comportamento visível. É uma **refatoração**: o código muda por dentro e o sistema continua igual por fora.

### Verificação
- `python manage.py test` → **21 testes, todos passando** (os testes de semestre que já existiam serviram de rede de segurança).
- Teste manual na página do curso: editar um semestre pelo modal salva, **fecha o modal** e atualiza o card sem recarregar a página. A alteração de teste foi desfeita em seguida.

---

## Melhoria 5 — Login obrigatório

### Problema
Fora o painel `/admin/`, **nenhuma página exigia autenticação**. Qualquer pessoa com acesso à rede podia ver dados pessoais dos alunos (nome, e-mail, RGM) e criar, editar ou excluir cursos, disciplinas, semestres e alunos.

### Por que importa
- **Segurança:** é o requisito mais básico de um sistema que altera dados.
- **Privacidade e LGPD:** nome, e-mail e RGM são dados pessoais. A Lei Geral de Proteção de Dados exige medidas que impeçam acesso não autorizado.
- **Rastreabilidade:** com usuários identificados, dá pra saber no futuro quem fez cada alteração.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `app/settings.py` | `LoginRequiredMiddleware` (nativo do Django desde a 5.1) adicionado ao `MIDDLEWARE`. `LOGIN_URL` e `LOGOUT_REDIRECT_URL` apontam pra tela de login do admin. |
| `templates/base.html` | O menu mostra o usuário logado e um botão **Sair** (logout via POST, com proteção CSRF). |
| `aluno/tests.py`, `curso/tests.py` | Os testes existentes passaram a logar um usuário (`force_login`), e há 2 testes novos (`LoginRequiredTests`): visitante é redirecionado nas 4 áreas, usuário logado acessa normalmente. |

### Decisões de design
- **Middleware em vez de `LoginRequiredMixin` em cada view:** a proteção é **"fechada por padrão"**. Toda página nova já nasce protegida, e ninguém precisa lembrar de adicionar o mixin. Esquecer uma view num sistema com 18 views é um erro fácil de cometer, e essa abordagem elimina esse risco.
- **Reaproveitar a tela de login do admin:** ela já existe, já tem o tema Jazzmin e já é segura, então não foi preciso criar template novo. **Limitação conhecida:** essa tela só aceita usuários marcados como "membro da equipe" (`is_staff`). Isso combina com o uso atual (secretaria e coordenação). Se no futuro alunos forem logar, será preciso criar uma tela de login própria.

### Verificação
- `python manage.py test` → **23 testes, todos passando**.
- Teste manual: acessar `/alunos/` sem login redireciona pra `/admin/login/?next=/alunos/`. Depois do login, o usuário volta direto pra página que tentou abrir.

---

## Melhoria 6 — Configuração segura para produção

### Problema
`settings.py` foi gerado pelo `startproject` e nunca foi ajustado pra produção:
- `SECRET_KEY` **escrita no código** e publicada no GitHub;
- `DEBUG = True` fixo: em produção, qualquer erro mostra código-fonte, variáveis e configurações pra quem estiver acessando;
- `ALLOWED_HOSTS = []` vazio;
- cookies de sessão e CSRF trafegando sem exigir HTTPS;
- `db.sqlite3` (com os dados dos alunos e o hash de senha do usuário admin) e 21 arquivos `__pycache__` **versionados no git**, sem `.gitignore`.

O comando oficial `python manage.py check --deploy` apontava **8 problemas**.

### Por que importa
- **`SECRET_KEY` exposta:** ela assina sessões, tokens CSRF e links de redefinição de senha. Quem tem a chave pode forjar uma sessão de login. Como já está no histórico do GitHub, **essa chave deve ser considerada comprometida** e nunca usada em produção.
- **`DEBUG` ligado:** vaza a estrutura interna do sistema justamente pra quem está procurando falhas.
- **Banco no git:** dados pessoais (LGPD) e hash de senha públicos no repositório. Cada commit do banco também gera conflitos entre os desenvolvedores.
- **Princípio dos *12 fatores*:** configuração que muda entre ambientes fica em **variáveis de ambiente**, não no código.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `app/settings.py` | `DEBUG`, `SECRET_KEY` e `ALLOWED_HOSTS` passaram a vir de variáveis de ambiente. Cookies seguros e redirecionamento pra HTTPS são ligados automaticamente fora do modo debug. Também removi a configuração de e-mail `MAILERS`, que não tinha uso (o sistema não envia e-mail) e era apontada como erro pelo `check --deploy`. |
| `.gitignore` (novo) | Ignora `db.sqlite3`, `__pycache__/`, `*.pyc`, `.env` e `.claude/`. |
| git | `db.sqlite3` e os 21 `__pycache__` removidos do controle de versão com `git rm --cached`. **Os arquivos continuam no disco**, só deixam de ser versionados. |

### Variáveis de ambiente
| Variável | Desenvolvimento (padrão) | Produção |
|---|---|---|
| `DJANGO_DEBUG` | `1` (não precisa definir) | `0` |
| `DJANGO_SECRET_KEY` | chave de dev automática | **obrigatória**: gerar com `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | vazio (localhost liberado pelo Django) | domínios separados por vírgula, ex.: `meusite.com,www.meusite.com` |

### Decisões de design
- **Seguro por padrão, prático no dia a dia:** sem nenhuma variável, o sistema roda em modo desenvolvimento como antes (`python manage.py runserver` continua funcionando). Já em produção (`DJANGO_DEBUG=0`), se a `SECRET_KEY` não estiver definida, **o sistema se recusa a iniciar** (`ImproperlyConfigured`) em vez de subir silenciosamente com uma chave fraca.
- **HSTS desligado de propósito:** o HSTS faz o navegador memorizar que o site só aceita HTTPS. Se for ativado antes de o HTTPS estar estável, o site fica inacessível pros visitantes durante todo o período configurado, e não dá pra desfazer pelo servidor. A recomendação é ativar só depois do deploy com HTTPS, começando com um valor baixo.
- **Consequência de tirar o banco do git:** quem clonar o projeto precisa criar o banco localmente:
  ```bash
  python manage.py migrate
  python manage.py populate_demo_data
  python manage.py createsuperuser
  ```

### Verificação
| Cenário | Resultado |
|---|---|
| `check --deploy` antes | **8 problemas** |
| `check --deploy` depois (produção configurada) | **1 aviso**: só o HSTS, desligado intencionalmente |
| Produção sem `DJANGO_SECRET_KEY` | o sistema recusa iniciar, com mensagem clara ✅ |
| Desenvolvimento sem variáveis | 23 testes passando, e o servidor sobe normalmente ✅ |

---

## Melhoria 7 — Frontend: funcionar offline e navegação mais fluida

Uma revisão do frontend apontou 4 problemas que afetavam diretamente o uso e a demonstração do sistema.

### 7.1 Bootstrap e HTMX servidos localmente (funciona sem internet)
**Problema:** o Bootstrap (CSS e JS) e o HTMX eram carregados de CDNs externos (`cdn.jsdelivr.net`, `unpkg.com`). Sem internet, por exemplo com Wi-Fi instável numa apresentação, o sistema aparecia **sem nenhum estilo**, e os modais de edição e exclusão **paravam de funcionar**.

**Por que importa:** além da disponibilidade, depender de servidores de terceiros significa que uma mudança ou instabilidade neles quebra o sistema. Servir os arquivos localmente também evita enviar dados de navegação dos usuários a terceiros.

**O que foi feito:**
- `static/vendor/` recebeu `bootstrap.min.css` e `bootstrap.bundle.min.js` (v5.3.3) e `htmx.min.js` (v2.0.4), **as mesmas versões** que já eram usadas (conferidas no cabeçalho de cada arquivo).
- `settings.py`: `STATICFILES_DIRS = [BASE_DIR / 'static']`.
- `base.html`: `{% load static %}` e links via `{% static %}`.
- **Fontes do Google mantidas de propósito:** o CSS já declara alternativas (`Georgia`, `system-ui`). Sem internet o visual muda só levemente, e nada quebra.

### 7.2 "Novo semestre" já vem com o curso preenchido
**Problema:** na página de um curso, o botão "Novo semestre" abria o formulário com o campo *Curso* em branco, obrigando a escolher de novo o curso em que o usuário já estava. Depois de salvar, o sistema voltava pra **lista de cursos**, e o usuário perdia o contexto.

**Por que importa:** cada passo desnecessário é uma chance de erro, como escolher o curso errado numa lista de 13. O fluxo esperado é: estou no curso → crio o semestre → volto pro curso e vejo o semestre novo.

**O que foi feito:**
- `course_detail.html`: os links passam `?course=<id>`.
- `SemesterCreateView`: `get_initial()` lê esse parâmetro e `get_success_url()` redireciona pra página do curso do semestre criado.

### 7.3 "Semestres" no menu
**Problema:** a página `/cursos/semestres/` (lista de todos os semestres, com busca) existia, mas **não tinha link em lugar nenhum**. Só dava pra chegar nela digitando o endereço.

**O que foi feito:** item "Semestres" no menu, destacado quando o usuário está em qualquer página de semestre.

### 7.4 Disciplinas em colunas
**Problema:** o formulário de semestre listava todas as 51 disciplinas cadastradas numa única coluna de checkboxes, gerando muita rolagem.

**O que foi feito:** 3 linhas de CSS com `column-width`. O navegador distribui em **quantas colunas couberem**: 1 no celular, 2 no formulário e 3 no modal, que é mais largo. Não precisou de JavaScript nem de alteração no Python.

### Verificação
- `python manage.py test` → **26 testes, todos passando**. Há 3 testes novos (`SemesterCreateFromCourseTests`): curso pré-preenchido, redirecionamento pro curso, e garantia de que **nenhum script vem de CDN**. Também atualizei 2 testes antigos que conferiam exatamente o comportamento substituído (HTMX via CDN e retorno à lista de cursos).
- No navegador: o único recurso externo carregado é a fonte do Google. O curso vem pré-selecionado, "Semestres" aparece no menu e as disciplinas ficam em 2 colunas.

**Observação pra produção:** com `DEBUG=0`, o Django não serve arquivos estáticos sozinho. No deploy, rode `python manage.py collectstatic` e configure o servidor web (ou o pacote WhiteNoise) pra servir `STATIC_ROOT`.

---

## Melhoria 8 — Identidade visual alinhada à Unigran

### Objetivo
Alinhar o visual do sistema à identidade da instituição, usando como referência o site oficial (unigran.br/campogrande), pra que ele pareça parte do ecossistema digital da universidade.

### Análise do site de referência
As cores e fontes foram **medidas no próprio site**, com os estilos calculados pelo navegador, e não estimadas a olho:

| Elemento | Valor | Uso no site |
|---|---|---|
| Azul institucional | `#034EA1` | barra superior, seções, botões, títulos |
| Amarelo | `#FDB913` | chamada principal ("INSCREVA-SE"), com texto azul em negrito |
| Azul-claro | `#6390C4` | cards de modalidade (cantos de 8px) |
| Cinza | `#DADEE2` | rodapé, com texto azul |
| Texto | `#09090B` | corpo do texto |
| Fonte | **Montserrat** (400–700) | todo o site |
| Botões | cantos de 4px, peso 600–700 | |
| Escrita | títulos e menus em **MAIÚSCULAS**, chamadas curtas e diretas | "ACESSO RÁPIDO", "VER TODOS OS CURSOS" |

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `templates/base.html` | Paleta trocada (variáveis CSS em `:root`), fonte Montserrat, menu azul com item ativo sublinhado em amarelo, títulos em maiúsculas, cabeçalho das tabelas em azul, cards de semestre com borda amarela e **rodapé cinza** no padrão do site. |
| `base.html` (nova classe `.btn-cta`) | Botão amarelo com texto azul, igual ao "INSCREVA-SE", usado na **ação principal** de cada tela ("Novo curso", "Nova disciplina", "Novo aluno", "Novo semestre"). Os demais botões (Buscar, Salvar) seguem o azul, como o "VER TODOS OS CURSOS". |
| 5 templates de listagem e detalhe | Botões "Novo …" passaram a usar `.btn-cta`. |
| `static/css/admin.css` (novo) + `settings.py` | Tela de login e painel admin (Jazzmin) com fundo azul, botão amarelo e Montserrat. O "Welcome" em inglês virou **"ACESSE A GESTÃO ACADÊMICA"**. |

### Decisões de design
- **Maiúsculas via CSS (`text-transform`), não no texto:** o HTML continua com "Novo curso". Leitores de tela leem normalmente (texto todo em maiúsculas costuma ser soletrado letra por letra), e a busca e os testes não mudam.
- **Amarelo só na ação principal:** como no site, o amarelo chama atenção pra **uma** ação por tela. Usar em todos os botões tiraria esse destaque.
- **Contraste (acessibilidade):** azul `#034EA1` com texto branco tem contraste de cerca de 8:1, e azul sobre amarelo cerca de 4,6:1. Os dois passam no critério WCAG AA (mínimo de 4,5:1).
- **Sem logotipo nem conteúdo institucional:** foram reaproveitadas só a paleta e a tipografia. O sistema não usa a marca nem os textos da Unigran e não se apresenta como site oficial, e o rodapé identifica o sistema como projeto acadêmico.

### Verificação
- `python manage.py test` → **26 testes, todos passando**. Só o visual mudou, nenhuma lógica.
- No navegador: as telas de cursos, detalhe do curso e login conferidas com o novo tema. No login, os estilos foram confirmados pelo navegador (fundo `#034EA1`, botão `#FDB913`, fonte Montserrat).

---

## Melhoria 9 — Página inicial com painel acadêmico

### Problema
O endereço raiz do sistema (`/`) retornava **erro 404 (página não encontrada)**. O sistema só começava em `/cursos/`, então quem digitava apenas o endereço caía numa tela de erro. Também não havia nenhuma visão geral: pra saber quantos alunos ou cursos existiam, era preciso abrir cada lista e olhar a paginação.

### Por que importa
- **Primeira impressão:** a página inicial é a porta de entrada. Um erro 404 ali passa a impressão de sistema quebrado.
- **Visão geral pra tomada de decisão:** coordenação e secretaria enxergam o estado do sistema em segundos.
- **Navegação:** atalhos pras tarefas mais comuns reduzem cliques.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `curso/views.py` | Nova view `dashboard`: totais de cursos, semestres, disciplinas e alunos, mais os **5 cursos com mais alunos**, calculados com `annotate(Count(...))`. A contagem é feita **no banco**, em uma única consulta, sem carregar os registros na memória. |
| `templates/dashboard.html` (novo) | 4 cards de números (cada um leva à sua lista), tabela "Cursos com mais alunos" (com semestres cadastrados × duração, ex.: "8 de 8") e bloco "Acesso rápido" com atalhos de cadastro, inspirado no "ACESSO RÁPIDO" do site da Unigran. |
| `app/urls.py` | Rota `''` → `dashboard` (nome `home`). |
| `templates/base.html` | Item "Início" no menu, logo "GESTÃO ACADÊMICA" apontando para o painel, estilos dos cards (azul com borda inferior amarela) e espaçamento antes de "Administração" no menu. |
| `app/settings.py` | O link "Tela principal" do admin agora aponta pro painel (`/`). |

**Detalhe técnico:** `Count("students", distinct=True)` e `Count("semesters", distinct=True)` são usados juntos. Sem o `distinct`, o JOIN duplo do SQL multiplicaria as contagens (um curso com 4 alunos e 8 semestres apareceria com 32 de cada).

### Verificação
- `python manage.py test` → **28 testes, todos passando**. Há 2 testes novos (`DashboardTests`): os totais e o curso aparecem corretamente, e a página exige login.
- No navegador: o painel mostra 13 cursos, 99 semestres, 51 disciplinas e 49 alunos, e o ranking é liderado por Engenharia de Software (5 alunos).

---

## Melhoria 10 — Avisos de sucesso (toasts)

### Problema
Depois de cadastrar, editar ou excluir qualquer registro, **nenhuma mensagem confirmava que a ação deu certo**. Nos formulários de página inteira, o usuário era só redirecionado pra lista e precisava procurar o item pra ter certeza. Nos modais HTMX, o modal fechava sem nenhum aviso.

### Por que importa
- **Feedback é uma das heurísticas de usabilidade de Nielsen** ("visibilidade do status do sistema"): o usuário precisa saber o resultado de cada ação.
- **Evita ações repetidas:** sem confirmação, o usuário tende a clicar de novo em "Salvar" e pode tentar cadastrar duplicado.
- **Confiança:** principalmente na exclusão, saber *o que* foi excluído (com o nome) dá segurança.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `app/htmx.py` | Novo `SuccessFeedbackMixin`, com a mensagem definida por view (`success_message`, aceitando `{object}`). Os dois mixins HTMX já existentes herdam dele, então **todas** as edições e exclusões ganharam o aviso automaticamente. |
| `curso/views.py`, `aluno/views.py` | As 12 views de cadastro, edição e exclusão ganharam mensagens no gênero certo ("Disciplina … cadastrad**a**", "Curso … cadastrad**o**"). |
| `templates/base.html` | Container de toasts (azul com borda amarela, abaixo do menu, some sozinho em 4s e tem botão de fechar) e a função `showToast()`. |

### Como funciona (dois caminhos)
1. **Formulário de página inteira (cadastro):** usa o **framework de mensagens do Django** (`django.contrib.messages`). A mensagem é guardada na sessão, sobrevive ao redirecionamento e aparece na página seguinte.
2. **Modal HTMX (edição e exclusão):** a página **não recarrega**, então uma mensagem na sessão só apareceria na próxima navegação, fora de contexto. Por isso a mensagem vai no cabeçalho `HX-Trigger-After-Swap`, como JSON `{"actionModalDone": null, "showMessage": "…"}`. O HTMX dispara o evento `showMessage`, e o JavaScript mostra o toast na hora.

### Detalhes técnicos
- **Acentos em cabeçalho HTTP:** cabeçalhos HTTP só aceitam ASCII com segurança. `json.dumps` converte "ã" em `ã`, e o navegador decodifica de volta. Há um teste que garante que o cabeçalho é ASCII.
- **Nome certo na exclusão:** o texto da mensagem é montado **antes** de excluir, enquanto o objeto ainda existe.
- **Exclusão bloqueada não mostra sucesso:** se a exclusão falha (curso com alunos, Melhoria 1), a mensagem não é gerada, porque ela só é registrada depois que a operação dá certo.
- **Segurança (XSS):** o toast usa `textContent`, nunca `innerHTML`, pro texto do usuário. Um curso chamado `<script>…` aparece como texto e não é executado.

### Verificação
- `python manage.py test` → **32 testes, todos passando**. Há 4 testes novos (`SuccessMessageTests`): mensagem após o redirecionamento, mensagem no cabeçalho HTMX (com o nome atualizado e o cabeçalho em ASCII), exclusão com o nome antigo, e exclusão bloqueada sem aviso de sucesso. Também atualizei 1 teste antigo, porque o cabeçalho passou de texto pra JSON.
- No navegador: editar "Administração" pelo modal fecha o modal e mostra o toast *"Curso "Administração" atualizado com sucesso."*

---

## Melhoria 11 — Arquivo de dependências (`requirements.txt`)

### Problema
O projeto **não tinha nenhum arquivo listando as bibliotecas necessárias**. Quem clonasse o repositório só descobriria o que instalar tentando rodar e lendo os erros um a um: primeiro `No module named 'django'`, depois `No module named 'jazzmin'`. Também não havia registro das **versões**, então outra pessoa poderia instalar uma versão diferente do Django, com comportamento diferente.

### Por que importa
- **Reprodutibilidade:** o sistema precisa funcionar igual na máquina de qualquer desenvolvedor, do professor avaliador ou do servidor de produção.
- **Onboarding:** um comando (`pip install -r requirements.txt`) substitui a tentativa e erro.
- **Padrão da comunidade Python:** é o primeiro arquivo que um desenvolvedor procura num projeto Python.

### O que foi feito
`requirements.txt` (novo, na raiz do repositório):
```
Django==6.1.3
django-jazzmin==3.0.5
```

### Decisões de design
- **Só dependências diretas:** um levantamento dos `import` do código mostrou que o projeto usa só duas bibliotecas externas, `django` e `jazzmin`. As dependências *delas* (`asgiref`, `sqlparse`, `tzdata`) são instaladas automaticamente pelo pip. Listá-las à mão criaria trabalho de manutenção sem benefício.
- **Versões exatas (`==`):** são as versões em que os 32 testes passam. Atualizar passa a ser uma decisão consciente (atualiza, roda os testes, confirma) e não uma surpresa.
- **Versão do Python documentada no arquivo:** o Django 6.1 exige Python 3.12 ou mais novo.

### Verificação
Criei um **ambiente virtual vazio** (`python -m venv`), instalei **só** a partir do `requirements.txt` e rodei a suíte:
- O pip instalou automaticamente as 5 bibliotecas (as 2 diretas + 3 dependências).
- `manage.py test` nesse ambiente limpo → **32 testes, todos passando** ✅

### Como rodar o projeto do zero
```bash
pip install -r requirements.txt
cd app
python manage.py migrate
python manage.py populate_demo_data
python manage.py createsuperuser
python manage.py runserver
```

---

## Melhoria 12 — Botão "Cancelar" com destino fixo

### Problema
Nos formulários de cadastro e edição e na tela de confirmação de exclusão, o botão "Cancelar" usava `href="javascript:history.back()"`, ou seja, "volte pra página anterior do histórico do navegador". Isso falha em vários casos reais:
- **link aberto direto** (favorito, link colado, nova aba): não há página anterior, e o botão não faz nada ou leva pra uma aba em branco;
- **depois de um erro de validação:** o formulário foi reenviado, então "voltar" leva ao próprio formulário com os dados antigos, e não à lista;
- **JavaScript desativado ou bloqueado:** o link simplesmente não funciona.

### Por que importa
- **Previsibilidade:** "Cancelar" deve sempre levar ao mesmo lugar lógico, independentemente de como o usuário chegou ali.
- **Acessibilidade e boas práticas:** links `javascript:` não são links de verdade. Leitores de tela e o "abrir em nova aba" não funcionam com eles.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `app/htmx.py` | `SuccessFeedbackMixin` ganhou `get_cancel_url()` e coloca `cancel_url` no contexto. O padrão é a mesma página pra onde o sistema vai depois de salvar (`success_url`), por exemplo a lista de cursos. Como **todas** as views de formulário e de exclusão já usam esse mixin (Melhoria 10), bastou mudar num lugar. |
| `curso/views.py` | `SemesterCreateView.get_cancel_url()`: se o usuário veio da página de um curso (`?course=ID`), "Cancelar" volta **pra esse curso**. Senão, vai pra lista de semestres. |
| `templates/form.html`, `templates/confirm_delete.html` | `href="javascript:history.back()"` → `href="{{ cancel_url }}"`. |

**Validação do parâmetro da URL:** `?course=` vem do navegador, então qualquer pessoa pode digitar qualquer coisa ali. O valor só é usado se for numérico **e** se o curso existir. Caso contrário, o sistema usa a lista de semestres. Isso evita erro 500 com `?course=abc` ou com um ID inexistente.

### Verificação
- `python manage.py test` → **35 testes, todos passando**. Há 3 testes novos (`CancelButtonTests`): as **12 páginas** de formulário e exclusão têm "Cancelar" com o destino esperado e nenhuma usa `history.back`, o fluxo a partir de um curso volta pro curso, e parâmetros inválidos (`abc`, `999999`, `<script>`) caem na lista de semestres.
- No navegador: abri `/alunos/novo/` numa **aba nova, sem histórico**. Clicar em "Cancelar" levou à lista de alunos. Antes, o botão voltaria pra uma página em branco.

---

## Melhoria 13 — Matrícula, notas e frequência (boletim)

### Problema
O sistema cadastrava cursos, disciplinas, semestres e alunos, mas **não ligava o aluno às disciplinas**. Não era possível registrar em quais disciplinas o aluno está matriculado, nem lançar notas, frequência ou situação (aprovado ou reprovado). Isso é o centro de um sistema de gestão acadêmica: sem essa parte, ele era só um cadastro.

### Por que importa
- **Completa o domínio:** curso → semestre → disciplina → **aluno matriculado com nota**. Agora o sistema responde perguntas reais, como "esse aluno foi aprovado em Cálculo?" e "qual a média dele?".
- **Regras de negócio reais:** aprovação depende de nota **e** de frequência, como exige a legislação.

### Modelagem
Novo modelo `Enrollment` (Matrícula) no app `aluno`:

| Campo | Tipo | Regra |
|---|---|---|
| `student` | FK → Aluno | `CASCADE`: excluir o aluno exclui as matrículas dele |
| `discipline` | FK → Disciplina | `PROTECT`: disciplina com notas lançadas **não pode ser excluída** (preserva o histórico e reaproveita o aviso amigável da Melhoria 1) |
| `grade` | Decimal (0–10, 2 casas) | opcional: vazio enquanto não houver nota |
| `attendance` | Inteiro (0–100 %) | opcional |

- **Unicidade:** `UniqueConstraint(student, discipline)`, então o aluno não pode se matricular duas vezes na mesma disciplina. A regra também existe no banco.
- **Só disciplinas do curso:** `clean()` rejeita uma disciplina que não está na grade do curso do aluno.
- **Situação calculada (`status`)**, sem ser armazenada no banco. É derivada da nota e da frequência, então nunca fica desatualizada:

| Condição | Situação |
|---|---|
| sem nota ou sem frequência | Cursando |
| frequência < 75% | **Reprovado por falta** (mesmo com nota 10) |
| nota < 6,0 | Reprovado |
| caso contrário | Aprovado |

**Base legal:** a frequência mínima de 75% é exigência da LDB (Lei 9.394/96, art. 24). A **média 6,0** é um padrão comum, mas varia entre instituições, por isso fica numa constante (`APPROVAL_GRADE`) fácil de ajustar.

### Telas
| Tela | O que faz |
|---|---|
| **Página do aluno** (`/alunos/<id>/`, novo) | Dados do aluno, 3 cards (disciplinas, aprovações, média geral) e **boletim** com nota, frequência e situação em selo colorido (verde aprovado, cinza cursando, vermelho reprovado). O nome do aluno na lista agora leva pra cá. |
| **Matricular em disciplina** | O formulário oferece **só** disciplinas da grade do curso do aluno que ele **ainda não cursa**. Não dá pra escolher errado. |
| **Lançar nota** (modal HTMX) | Atualiza só a linha do boletim. A situação muda na hora (ex.: Cursando → Aprovado), com aviso de sucesso. |
| **Excluir matrícula** (modal HTMX) | Remove a linha, com confirmação. |
| **Admin** | Matrículas editáveis dentro da ficha do aluno (inline). |

**Reaproveitamento:** os modais de nota e exclusão usam os mesmos mixins (`HtmxModalUpdateMixin` e `HtmxModalDeleteMixin`) e os mesmos templates de modal das outras telas. Foi preciso só **configurar**, sem lógica nova de HTMX.

### Dados de demonstração
O `populate_demo_data` agora matricula cada aluno de demonstração nas disciplinas dos 2 primeiros semestres do curso: o 1º semestre já avaliado e o 2º em andamento. As notas são **determinísticas** (calculadas a partir dos IDs), então são as mesmas a cada execução. Resultado: 296 matrículas, sendo 94 aprovados, 34 reprovados, 24 reprovados por falta e 144 cursando.

### Verificação
- `python manage.py test` → **43 testes, todos passando**. Há 8 testes novos (`EnrollmentTests`): regras de situação (incluindo os limites exatos 6,0 e 75% e "nota 10 com 74% reprova por falta"), formulário oferecendo só disciplinas válidas, rejeição de disciplina de outro curso, redirecionamento com aviso, lançamento de nota via HTMX atualizando a situação, nota e frequência fora da faixa rejeitadas, média e aprovações do boletim, e disciplina com notas protegida contra exclusão.
- No navegador: o boletim da aluna "Ana Beatriz Almeida" mostra 8 disciplinas, 5 aprovações e média 8,5. Lancei nota 8,0 e 85% em "Banco de Dados" pelo modal: a linha passou de *Cursando* pra *Aprovado* sem recarregar a página. O teste foi desfeito depois.

---

## Melhoria 14 — Semestres gerenciados dentro do curso

### Problema
O menu tinha uma aba **"Semestres"** com uma lista solta de todos os semestres de todos os cursos (99 registros, 5 por página). Um semestre, porém, **não existe sozinho**: ele é parte da grade de um curso ("3º semestre de Direito"). A lista separada:
- mostrava semestres fora de contexto, misturando cursos diferentes;
- duplicava o que a página do curso já mostra melhor (a grade completa em cards);
- deixava a navegação confusa, com dois caminhos pra mesma informação e retornos inconsistentes (editar um semestre pela página do curso voltava pra lista solta).

### Por que importa
- **O modelo mental do usuário:** quem trabalha na secretaria pensa "vou montar a grade **do curso** X", não "vou gerenciar semestres". A interface agora segue a hierarquia real: **Curso → Semestres → Disciplinas**.
- **Menos é mais:** um item a menos no menu e uma tela a menos pra manter.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `templates/base.html` | Item "Semestres" removido do menu. Nas páginas de semestre, o item **Cursos** fica destacado. |
| `curso/views.py` | `SemesterListView` removida. Novo `SemesterCourseRedirectMixin`: editar, excluir e cancelar um semestre **sempre voltam pra página do curso** dele. `SemesterDeleteView` passou a usar o `HtmxModalDeleteMixin` (exclusão por modal, sem recarregar). O card "Semestres" do painel leva pra lista de cursos. |
| `curso/urls.py` | Rota `/cursos/semestres/` removida (agora retorna 404). |
| `templates/curso/semester_list.html` | Removido. |
| `templates/curso/partials/semester_card.html` | Botão **Excluir** ao lado de "Editar" em cada card. A confirmação abre no modal e o card some da grade na hora, com aviso de sucesso. |

**Antes × depois:**
| Ação | Antes | Depois |
|---|---|---|
| Ver semestres | Aba "Semestres" (lista misturada) ou curso | Página do curso |
| Criar semestre | Página do curso | Página do curso (curso já preenchido) |
| Editar semestre | Modal no curso | Modal no curso |
| Excluir semestre | Só abrindo o detalhe do semestre | **Modal direto no card** |
| Depois de salvar ou excluir | Ia pra lista solta | **Volta pro curso** |

### Verificação
- `python manage.py test` → **47 testes, todos passando**. Há 4 testes novos (`SemestersInsideCourseTests`): a rota antiga dá 404 e o menu não tem mais "Semestres", o card oferece "Excluir", a exclusão via HTMX remove o card com aviso, e a exclusão em página inteira volta pro curso. Também atualizei os testes antigos de "Cancelar", que esperavam a lista de semestres.
- No navegador: o menu mostra Início, Cursos, Disciplinas e Alunos. Na página de "Administração", o "Excluir" do 1º semestre abriu a confirmação no modal. Cancelei o teste, sem excluir nada.

---

## Melhoria 15 — Boletim em PDF

### Objetivo
Permitir **emitir o boletim do aluno como documento**: salvar em PDF, imprimir ou entregar. É a "saída" concreta do sistema, aquilo que o aluno de fato recebe.

### Decisão de design: PDF nativo do navegador, sem biblioteca
Há duas formas de gerar PDF numa aplicação web:

| Abordagem | Prós | Contras |
|---|---|---|
| Biblioteca no servidor (WeasyPrint, ReportLab) | gera o arquivo sem interação; dá pra anexar em e-mail | **dependência nova**. O WeasyPrint precisa de bibliotecas do sistema (GTK/Pango) e é difícil de instalar no Windows. O ReportLab exige desenhar o layout em código Python, sem reaproveitar HTML e CSS. |
| **Página HTML + CSS de impressão + "Salvar como PDF" do navegador** ✅ | **zero dependências**, funciona offline e em qualquer navegador, o layout é HTML e CSS comuns (fácil de manter) e a mesma página serve pra imprimir no papel | o usuário escolhe "Salvar como PDF" no diálogo de impressão |

Escolhi a segunda: atende ao caso de uso (emitir e imprimir o boletim) sem nenhuma dependência nova. O código tem um comentário (`ponytail:`) indicando quando valeria trocar por uma biblioteca, por exemplo pra enviar boletins por e-mail automaticamente.

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `aluno/views.py` | `ReportCardView`: herda de `StudentDetailView` e reaproveita **os mesmos cálculos** (média, aprovações, matrículas). Só troca o template e acrescenta a data de emissão. |
| `aluno/urls.py` | Rota `/alunos/<id>/boletim/`. |
| `templates/aluno/report_card.html` (novo) | Documento independente (sem menu nem rodapé do sistema), em formato **A4** (`@page { size: A4 }`). Tem cabeçalho com a identidade visual, dados do aluno, resumo (disciplinas, aprovações, média), tabela com carga horária, nota, frequência e situação, regra de aprovação, data e hora de emissão e linha de assinatura da secretaria. Um botão "Salvar em PDF / Imprimir" chama `window.print()` e some na impressão. |
| `templates/aluno/student_detail.html` | Botão **"Boletim em PDF"** (abre em nova aba). |
| `templates/base.html` | Botão contornado (`btn-outline-primary`) no azul da identidade visual. |
| `app/settings.py` | `TIME_ZONE` de `UTC` → **`America/Campo_Grande`**. Sem isso, a data de emissão do boletim sairia 4 horas adiantada. |

### Detalhes técnicos de impressão
- **`print-color-adjust: exact`**: por padrão, navegadores **removem cores de fundo** ao imprimir, pra economizar tinta. Sem essa regra, o cabeçalho azul da tabela e os cards sairiam brancos.
- **`<title>` = nome do arquivo:** o navegador sugere o título da página como nome do PDF, então ele já sai como `Boletim - Ana Beatriz Almeida - RGM 0080004.pdf`.
- **`break-inside: avoid`** nas linhas: num boletim longo, nenhuma linha da tabela é cortada ao meio entre duas páginas.

### Verificação
- `python manage.py test` → **50 testes, todos passando**. Há 3 testes novos (`ReportCardTests`): o documento contém os dados, as regras de impressão e nenhum menu do sistema; a página do aluno tem o link; e o boletim exige login.
- **PDF real gerado** com o Microsoft Edge em modo headless (`--print-to-pdf`): **1 página A4** com as cores preservadas, todos os dados corretos e a data de emissão no fuso de Campo Grande. O exemplo está salvo em `boletim-exemplo.pdf`, na pasta do projeto.

---

## Melhoria 16 — QR Code de verificação do boletim

### Objetivo
Cada boletim ganha um **QR Code**. Ao escanear com o celular, abre a versão **oficial e atualizada** do boletim direto do sistema. Serve pra dois usos:
1. **Verificar a autenticidade** de um boletim impresso. É o mesmo princípio dos diplomas digitais e das notas fiscais: se alguém alterar uma nota no papel, o QR mostra o valor verdadeiro.
2. **Demonstração:** o visitante aponta o celular pra tela e vê o boletim no próprio aparelho.

### O desafio: o sistema exige login
Desde a Melhoria 5, **toda página exige login**. Um QR apontando pro boletim normal levaria o visitante à tela de login. Liberar o boletim (`/alunos/33/boletim/`) também não serve: qualquer pessoa trocaria o `33` por `34` e veria as notas de outro aluno.

### Solução: link assinado criptograficamente
O QR leva a `/boletim/<token>/`, onde o token é o ID do aluno **assinado com a `SECRET_KEY`** usando `django.core.signing`, que já vem no Django:
```
/boletim/MzM:1xOkRl:jYQbyHS7e5DwJt_0ovSa-SoQ05MWHvCyj5qX2ob5rnA/
         └ID┘       └──────── assinatura HMAC-SHA256 ────────┘
```
- **Não dá pra adivinhar:** sem a `SECRET_KEY`, é impossível gerar o token de outro aluno.
- **Não dá pra adulterar:** mudar um único caractere invalida a assinatura e o sistema responde **404**.
- **Salt próprio** (`"aluno.boletim"`): mesmo outra assinatura válida do Django não serve como token de boletim.
- **Sem banco de dados:** o token não é armazenado, então não foi preciso criar migração nem tabela.

### Privacidade (LGPD)
A página pública é **só de leitura** e mostra o mínimo necessário: nome, RGM, curso e notas. O **e-mail do aluno é omitido**. O botão "Voltar" (que levaria ao sistema interno) também não aparece. Essa é a **única** rota liberada do login, marcada explicitamente com `login_not_required` em `app/urls.py`. Todas as outras continuam protegidas (há um teste pra isso).

### O que foi feito
| Arquivo | Alteração |
|---|---|
| `requirements.txt` | `segno==1.6.6`: gera QR Code em Python puro, **sem nenhuma dependência**. Saída em SVG (vetorial), então fica nítido na tela e no PDF. |
| `aluno/views.py` | `report_card_url()` (gera o link assinado), `qr_svg()` (gera o QR em azul `#034EA1`) e `PublicReportCardView`, que valida o token e responde 404 se for inválido. A página do aluno e o boletim ganham o QR no contexto. |
| `app/urls.py` | Rota pública `/boletim/<token>/`, com `login_not_required`. |
| `templates/aluno/report_card.html` | QR no rodapé ("Verifique a autenticidade"). Na versão pública, selo verde **"✓ Documento autêntico"**, sem e-mail e sem "Voltar". **Layout responsivo pro celular**: a folha A4 vira página fluida, e a coluna de carga horária e os códigos somem pra nota, frequência e situação caberem em 375px sem rolagem lateral. |
| `templates/aluno/student_detail.html` | Card **"Boletim no celular"** com o QR ao lado dos números. Clicar no QR abre o link público. |
| `app/settings.py` | Em **desenvolvimento**, `ALLOWED_HOSTS` aceita qualquer endereço, pra o celular acessar pelo IP da rede, seja qual for o Wi-Fi. Em **produção** (`DJANGO_DEBUG=0`), continua exigindo a lista explícita. |
| `feira.bat` (novo, na pasta do projeto) | Dois cliques: **mostra os endereços de rede** do computador e sobe o servidor acessível pela rede local (`0.0.0.0:8000`). |

### Por que o endereço importa
Por padrão, o link do QR usaria o endereço **pelo qual a página foi aberta**. No teste real, o sistema estava aberto no computador como `127.0.0.1:8000`, e o celular foi mandado pra `127.0.0.1`, que **no celular é o próprio celular**, então não abriu.

**Correção automática:** quando a página é acessada por um endereço local (`127.0.0.1`, `localhost`, `[::1]`), o sistema troca o host do link pelo **IP do computador na rede**. A função `lan_ip()` descobre esse IP com um `connect` UDP, que **não envia nenhum pacote**: só pergunta ao sistema operacional qual interface seria usada pra sair, e retorna o IP dela (aqui, `192.168.30.78`). Se não houver rede, o link mantém o endereço original. Quando a página já é aberta pelo IP da rede, o endereço é mantido como está. Assim, o QR funciona **seja qual for o endereço digitado no computador**.

**Requisito que continua valendo:** o servidor precisa aceitar conexões da rede (`runserver 0.0.0.0:8000`, que é o que o `feira.bat` faz). O `runserver` puro só atende o próprio computador.

### Verificação
- `python manage.py test` → **54 testes, todos passando**, também num **ambiente virtual limpo** instalado só pelo `requirements.txt` (agora com o `segno`). Há 4 testes novos (`PublicReportCardTests`): o QR aparece no boletim e na página do aluno; o link abre **sem login**, com o selo e **sem e-mail**; tokens **adulterados**, o ID puro (`/boletim/33/`) e um token **assinado com outro salt** dão 404; e as outras páginas continuam exigindo login.
- No navegador: aberto pelo IP do Wi-Fi, o QR da aluna Ana Beatriz aponta pra `http://192.168.3.199:8000/boletim/…`. Abri esse link numa tela de **375px (celular)** e a página coube sem rolagem lateral, com o selo de autenticidade, notas e situação visíveis.
- O PDF de exemplo (`boletim-exemplo.pdf`) foi gerado de novo, com o QR no rodapé, em 1 página A4.
- **Primeiro teste com celular falhou, e foi diagnosticado:** o QR apontava pra `192.168.3.199`, um IP **antigo** do adaptador Wi-Fi, que estava desconectado (o Windows ainda listava o endereço com estado *Deprecated*). O computador estava ligado só pelo cabo de rede (`192.168.30.78`). O firewall não era a causa: já havia regra permitindo o Python. Correção: o `feira.bat` passou a listar **só endereços ativos** (`AddressState = Preferred`), e o sistema foi reaberto pelo IP correto.
- **Segundo teste também falhou, e foi corrigido no código:** o sistema estava aberto no Chrome como `127.0.0.1`, então o QR apontava pra `127.0.0.1`. Agora o IP da rede é detectado automaticamente (seção acima). Há 3 testes novos (`QrHostTests`): o acesso por `127.0.0.1` e por `localhost` gera o QR com o IP da rede, o acesso pelo IP da rede mantém o próprio endereço, e o link gerado abre sem login. O QR na página do aluno também foi **aumentado de 88 para 132 px**, pra facilitar a leitura pela câmera. **Total: 57 testes passando.**

---

## Resumo geral

| # | Melhoria | Categoria | Testes novos |
|---|---|---|---|
| 1 | Exclusão bloqueada mostra aviso em vez de erro 500 | Experiência do usuário | 2 |
| 2 | Semestres sem duplicidade e dentro da duração do curso | Integridade de dados | 4 |
| 3 | RGM padronizado em 7 dígitos, com migração dos dados | Integridade de dados | 2 |
| 4 | Edição de semestre reaproveita o mixin HTMX | Qualidade de código | — (1 asserção) |
| 5 | Login obrigatório em todo o sistema | Segurança | 2 |
| 6 | Configuração por variáveis de ambiente e banco fora do git | Segurança | — (verificado via `check --deploy`) |
| 7 | Frontend offline, "Novo semestre" com curso, menu e colunas | Experiência do usuário | 3 |
| 8 | Identidade visual alinhada à Unigran | Design / identidade visual | — (verificado no navegador) |
| 9 | Página inicial com painel acadêmico | Experiência do usuário | 2 |
| 10 | Avisos de sucesso (toasts) em todas as ações | Experiência do usuário | 4 |
| 11 | `requirements.txt` com versões fixas | Reprodutibilidade | — (verificado em ambiente limpo) |
| 12 | Botão "Cancelar" com destino fixo | Experiência do usuário / acessibilidade | 3 |
| 13 | Matrícula, notas, frequência e boletim | Nova funcionalidade | 8 |
| 14 | Semestres gerenciados dentro do curso | Navegação / arquitetura da informação | 4 |
| 15 | Boletim em PDF (A4, pronto pra impressão) | Nova funcionalidade | 3 |
| 16 | QR Code de verificação com link assinado | Nova funcionalidade / segurança | 7 |

**Suíte de testes:** de 13 para **57 testes**, todos passando.

## Próximos passos sugeridos
- Gerar uma **nova `SECRET_KEY`** para qualquer ambiente real (a antiga está no histórico do Git).
- Ativar **HSTS** depois do deploy com HTTPS.
- Criar uma **tela de login própria**, caso alunos passem a acessar o sistema.
- Registrar **quem alterou o quê** (auditoria), aproveitando que agora há usuários identificados.
