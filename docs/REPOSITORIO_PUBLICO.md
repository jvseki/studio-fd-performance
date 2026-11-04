# Repositório público e arquivos locais

Este repositório publica o código do Studio FD Performance, testes com dados
fictícios, scripts de desenvolvimento e documentação técnica.

## O que fica fora

O `.gitignore` exclui bancos SQLite, dados locais, contratos, backups, logs,
exportações, instaladores, ambientes Python, credenciais, arquivos `.env`,
certificados e chaves. Também exclui capturas de tela, a logo original do cliente
e o lembrete local com condições comerciais. Esses arquivos continuam no computador.

Use a pasta `privado/` para novas anotações comerciais ou pessoais do projeto.
Não coloque senhas ou tokens no código. Os nomes, telefones e CPFs dos testes
são exemplos fictícios para validar os formulários; não substitua por dados reais.

## Antes de enviar mudanças

Confira no painel **Controle do Código-Fonte** do VS Code os arquivos e as linhas
que entrarão no commit. No terminal, os comandos equivalentes são:

```powershell
git status --short
git diff --cached --stat
git diff --cached
```

Arquivos ignorados não são enviados por um `git add` normal. Isso não é criptografia,
backup nem uma garantia de que todo conteúdo sensível será detectado: um segredo
escrito dentro de um arquivo Python também seria publicado se você o incluísse.
Evite `git add -f`, pois ele pode incluir arquivos ignorados.

O GitHub não oferece visibilidade privada para arquivos individuais dentro de um
repositório público. Se precisar guardar material confidencial online, utilize
um repositório privado separado ou um backup com acesso restrito. Não envie o banco
de alunos ao GitHub como forma de backup.

## Cuidados com o histórico

Adicionar ao `.gitignore` um arquivo que já foi publicado não remove o histórico.
Se uma credencial vazar, revogue-a e substitua-a; apagar a linha no próximo commit
não basta. Evite anexar dados de alunos a issues, comentários, releases ou imagens.

Os commits deste projeto usam o endereço `noreply` do GitHub para preservar o
e-mail pessoal do autor. Essa configuração é local ao repositório.

Referências: [arquivos ignorados no GitHub](https://docs.github.com/en/get-started/git-basics/ignoring-files)
e [e-mail usado nos commits](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).
