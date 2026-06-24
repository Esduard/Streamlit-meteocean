# MeteoceanForecast

Este documento explica como instalar e utilizar o executável **MeteoceanForecast** no Windows.

## 1. Recebimento do arquivo

Você receberá um arquivo compactado chamado:

```text
MeteoceanForecast.zip
```

Antes de executar a aplicação, é necessário **descompactar o arquivo `.zip`**.

## 2. Como descompactar

1. Clique com o botão direito sobre `MeteoceanForecast.zip`.
2. Selecione **Extrair tudo** ou **Extract All**.
3. Escolha uma pasta de destino no computador.
4. Após a extração, será criada uma pasta chamada:

```text
MeteoceanForecast
```

Dentro dessa pasta estará o executável da aplicação:

```text
MeteoceanForecast.exe
```

> Importante: não execute o programa diretamente de dentro do `.zip`. Primeiro extraia todos os arquivos.

## 3. Criando um atalho na Área de Trabalho

Para facilitar o uso diário, recomenda-se criar um atalho do executável na Área de Trabalho.

1. Abra a pasta `MeteoceanForecast`.
2. Localize o arquivo `MeteoceanForecast.exe`.
3. Clique com o botão direito sobre ele.
4. Selecione **Enviar para > Área de Trabalho (criar atalho)**.

Assim, você poderá abrir a aplicação diretamente pela Área de Trabalho, sem precisar entrar manualmente na pasta do programa.

> Não mova apenas o `.exe` para fora da pasta. O executável depende dos arquivos internos da pasta para funcionar corretamente. Use sempre um **atalho**.

## 4. Abrindo a aplicação

Para iniciar a aplicação:

1. Dê dois cliques em `MeteoceanForecast.exe` ou no atalho criado na Área de Trabalho.
2. Uma janela de terminal do Windows será aberta.
3. Aguarde alguns instantes enquanto a aplicação carrega os arquivos necessários.
4. Após o carregamento, uma aba do navegador será aberta automaticamente.

A aplicação roda localmente no seu computador, por meio do navegador, usando um endereço parecido com:

```text
http://localhost:8501
```

Caso a porta `8501` já esteja ocupada, a aplicação poderá usar outra porta automaticamente.

> Enquanto estiver utilizando a aplicação, mantenha a janela do terminal aberta. Fechar o terminal encerra a aplicação.

## 5. Tela inicial

Ao abrir a aplicação, a página inicial exibirá a seção **Available Models**.

Essa seção carrega os modelos disponíveis a partir da pasta interna `models`.

Aguarde até que a lista de modelos seja carregada. A tabela pode mostrar informações como:

* Nome do modelo;
* Variável alvo;
* Tipo do modelo;
* Se o modelo é univariado ou exógeno;
* Features necessárias;
* Horizonte máximo de previsão.

Nesta versão inicial, o modelo disponível é para previsão de **velocidade de corrente**.

Modelos para **altura de onda** e **velocidade de vento** ainda não estão disponíveis nesta versão.

## 6. Usando o modelo univariado

A versão inicial deve ser utilizada preferencialmente com o modelo **univariado**.

1. Na interface, selecione o modelo univariado.
2. Escolha o horizonte de previsão desejado.
3. O horizonte representa quantas horas à frente o modelo irá prever.
4. O limite máximo disponível é de **8760 horas**, equivalente a aproximadamente um ano.
5. Clique em **Run Forecast** para executar a previsão.

Após a execução, a aplicação exibirá o resultado da previsão da velocidade de corrente.

O gráfico apresenta a previsão central e um intervalo de confiança de aproximadamente **95%**, com limites superior e inferior.

## 7. Baixando os resultados

Após rodar a previsão, será exibido um botão para download dos resultados:

```text
Download CSV
```

Clique nesse botão para baixar um arquivo `.csv` contendo os valores previstos.

Esse arquivo pode ser aberto em ferramentas como Excel, Python, R ou outros sistemas de análise de dados.

## 8. Sobre os modelos exógenos

A aplicação também exibe opções relacionadas a modelos exógenos.

No entanto, nesta versão inicial, o botão de upload de arquivos exógenos ainda **não está funcional**.

Mesmo que o botão apareça na interface e permita seleção de arquivo, essa funcionalidade será concluída em uma versão futura.

Para testes e uso inicial, recomenda-se utilizar o modelo **univariado**.

## 9. Observações importantes

* A aplicação roda localmente no computador do usuário.
* O navegador é usado apenas como interface visual.
* A janela do terminal deve permanecer aberta durante o uso.
* O executável depende dos arquivos internos da pasta extraída.
* Não remova, renomeie ou mova manualmente arquivos internos da pasta `MeteoceanForecast`.
* A versão atual inclui apenas previsão para velocidade de corrente.
* Funcionalidades adicionais, como modelos para onda, vento e upload de variáveis exógenas, serão adicionadas em versões futuras.

## 10. Encerrando a aplicação

Para fechar a aplicação:

1. Feche a aba do navegador.
2. Feche a janela do terminal aberta pelo executável.

Após isso, a aplicação será encerrada.
