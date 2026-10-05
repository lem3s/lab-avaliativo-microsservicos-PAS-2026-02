# Respostas — Laboratório Avaliativo de Microsserviços (PAS 2026/2)

**Dupla:** João Victor Lemes Faria · Yasmin Lopes de Moura

---

## Etapa 3 — Integração REST: experimento de consistência

**1. O que aconteceu com o estoque?**
O estoque foi reduzido e permaneceu reduzido. A reserva foi confirmada no banco do Estoque Service antes de a falha
acontecer no Pedido Service, e nada a desfez automaticamente. As unidades ficaram reservadas para um pedido que não
existe, deixando os dois bancos inconsistentes entre si. Quando a compensação está habilitada, o Pedido Service
solicita a liberação da reserva e o estoque volta ao valor anterior.

**2. O pedido foi criado?**
Não, a falha interrompeu a operação antes da gravação, a transação local do Pedido Service foi desfeita e o cliente
recebeu um erro. Como o pedido não existe, nenhum evento `pedido.criado` foi publicado.

**3. Existe uma transação única envolvendo os dois serviços?**
Não, cada serviço possui seu próprio banco de dados e sua própria transação local. A reserva é confirmada em uma
transação no banco do Estoque, e a criação do pedido ocorre em outra transação no banco do Pedido. Não existe um
coordenador de transação distribuída (como o 2PC), então desfazer uma transação não desfaz a outra. 

**4. Como o sistema poderia desfazer a reserva realizada?**
Por meio de uma ação de compensação em que o Estoque Service oferece uma operação de liberação que devolve ao estoque a quantidade reservada. Quando a criação do pedido falha após a reserva, o Pedido Service chama essa operação. 

**5. Que mecanismo poderia ser utilizado para realizar essa compensação?**
O padrão **Saga**, em que a operação distribuída é dividida em uma sequência de transações locais, e cada passo tem uma
transação compensatória que é executada se um passo posterior falhar. A Saga pode ser:
- **Orquestrada:** um serviço coordenador conduz os passos e dispara as compensações. Foi a abordagem adotada: o
  Pedido Service reserva, tenta criar o pedido e, em caso de falha, solicita a liberação.
- **Coreografada:** cada serviço reage a eventos publicados pelos demais. Por exemplo, um evento de falha do pedido
  seria consumido pelo Estoque, que liberaria a reserva.

Para que a compensação seja garantida mesmo se o Estoque estiver indisponível no momento da falha, ela deve ser
registrada de forma persistente e reexecutada até ter sucesso, por exemplo com o padrão **Transactional Outbox** ou
publicando a compensação em uma fila do RabbitMQ.

---

## Etapa 4 — Docker Compose

**O Pedido consegue acessar o Estoque?**
Sim, o Docker Compose coloca todos os serviços em uma mesma rede interna, na qual cada container é encontrado pelo
nome do serviço via DNS. O Pedido Service acessa o Estoque pelo endereço `http://estoque-service` na porta interna do
container. A porta publicada no host serve apenas para acesso externo. O fluxo de criação de pedido, que depende da
reserva no Estoque, funcionou normalmente.

---

## Etapa 5 — RabbitMQ

**1. Por que o Pedido Service publica em um Exchange em vez de enviar diretamente para uma Queue?**
No modelo do RabbitMQ (AMQP), o produtor publica em um exchange com uma routing key, e o exchange decide, pelos
bindings, para quais filas a mensagem será encaminhada. Isso desacopla o produtor da forma como as mensagens são
consumidas. É possível adicionar novas filas interessadas no mesmo evento (por exemplo, notificação ou auditoria),
mudar o roteamento ou configurar filas de mensagens mortas sem alterar o Pedido Service. O produtor apenas anuncia que
"um pedido foi criado", sem precisar saber quem se interessa por isso.

**2. Qual é a diferença entre Exchange, Queue e Consumer?**
- **Exchange:** ponto de entrada das mensagens. Não armazena nada; apenas roteia cada mensagem para zero ou mais filas
  de acordo com o seu tipo (direct, topic, fanout, headers) e com os bindings.
- **Queue:** armazena as mensagens até que sejam consumidas e confirmadas. Funciona como um buffer que permite que
  produtor e consumidor trabalhem em ritmos e momentos diferentes.
- **Consumer:** a aplicação que se inscreve em uma fila, recebe as mensagens, processa cada uma e confirma (ack) ou
  rejeita (nack). Neste laboratório, o Pagamento Service consome a fila `pedido.criado`.

**3. O Pedido Service sabe quem consumirá o evento?**
Não, ele conhece apenas o exchange (`pedidos.exchange`) e a routing key (`pedido.criado`). Não conhece o Pagamento
Service, seu endereço nem quantas instâncias existem. Por isso foi possível escalar o Pagamento (Etapa 10) sem nenhuma
alteração no Pedido Service.

---

## Etapa 7 — Teste funcional

Ao criar um pedido, foi verificado que:

1. **O estoque foi atualizado:** a quantidade do produto foi reduzida pela quantidade pedida.
2. **O pedido foi criado com status `AGUARDANDO_PAGAMENTO`:** a API respondeu com sucesso, retornando o pedido nesse status.
3. **O evento `pedido.criado` foi publicado:** a mensagem passou pelo exchange `pedidos.exchange` e chegou à fila `pedido.criado`.
4. **O Pagamento Service consumiu o evento:** o log do Pagamento registrou o recebimento e a fila foi esvaziada.
5. **O pagamento foi registrado no banco do Pagamento Service:** a tabela `pagamento` passou a ter um registro para o pedido.
6. **O resultado foi registrado no log:** o Pagamento registrou se o pagamento foi aprovado ou rejeitado.

---

## Etapa 8 — Simulação de falha

**1. O pedido foi criado?**
Sim. O Pedido Service depende do Pagamento apenas por meio do RabbitMQ. Como o RabbitMQ continuava disponível, o pedido
foi criado normalmente com status `AGUARDANDO_PAGAMENTO`.

**2. O estoque foi atualizado?**
Sim. A reserva de estoque é uma chamada síncrona ao Estoque Service, que não depende do Pagamento. O estoque foi
reduzido normalmente.

**3. O sistema inteiro parou?**
Não. Apenas o processamento de pagamentos ficou suspenso. A consulta de produtos, a reserva de estoque e a criação e
consulta de pedidos continuaram funcionando. Como a comunicação com o Pagamento é assíncrona, a falha ficou isolada
nesse serviço e não se propagou para os demais. Os pedidos apenas permaneceram aguardando pagamento.

**4. A mensagem foi perdida?**
Não. A mensagem ficou armazenada na fila `pedido.criado`, aguardando um consumidor:
- **No RabbitMQ:** a fila passou a mostrar mensagens prontas para entrega (*Ready*) e nenhum consumidor conectado.
  A fila passou a ter mensagens pendentes. 
- **Nos logs:** o Pedido Service registrou a criação do pedido e a publicação do evento. O Pagamento Service não
  registrou nenhum recebimento, pois estava parado.

Evidências: `docs/evidencias/05-fila-pedido-criado.png` mostra a fila `pedido.criado` com a mensagem pendente;
`06-payload-pedido-na-fila.png` mostra a fila sem consumidor conectado e o conteúdo da mensagem retida;
`07-log-pagamento.png` mostra o Pagamento Service encerrado antes da criação do pedido e o consumo da mensagem
somente após o serviço ser religado.

A mensagem não se perde porque a fila é durável e as mensagens são publicadas como persistentes, sendo mantidas em
disco pelo RabbitMQ até serem consumidas e confirmadas.

---

## Etapa 9 — Recuperação

**1. O processamento precisou ser repetido manualmente?**
Não. Assim que o Pagamento Service voltou e se conectou à fila, o RabbitMQ entregou automaticamente as mensagens
pendentes, e cada pedido foi processado. Nenhum pedido precisou ser reenviado.

**2. O Pedido Service precisou aguardar o Pagamento Service?**
Não. O Pedido Service respondeu ao cliente logo após publicar o evento, sem esperar pelo Pagamento. Os dois serviços
são desacoplados no tempo: o resultado do pagamento chega depois, pelo evento `pagamento.processado` (Etapa 12).

**3. O que aconteceu com as mensagens enquanto o consumidor estava indisponível?**
Ficaram armazenadas na fila, no estado *Ready*, persistidas pelo RabbitMQ. Uma mensagem só é removida da fila depois
da confirmação (ack) do consumidor; sem consumidor, nenhuma foi removida. Quando o serviço voltou, as mensagens foram
entregues em ordem e removidas da fila à medida que eram processadas e confirmadas.

---

## Etapa 10 — Escalabilidade

**As mensagens foram distribuídas?**
Sim. As duas instâncias do Pagamento Service se conectaram como consumidoras da mesma fila, e o RabbitMQ distribuiu as
mensagens entre elas (padrão *competing consumers*). Como cada instância recebe uma nova mensagem apenas depois de
confirmar a anterior, a instância mais livre acaba recebendo mais trabalho.

**Apenas uma instância processou cada mensagem?**
Sim. Em uma fila, cada mensagem é entregue a um único consumidor e removida após a confirmação. Cada pedido foi
processado por apenas uma das instâncias e gerou um único registro de pagamento. Além disso, o processamento é
idempotente: se uma mensagem for reentregue (por exemplo, se uma instância cair antes de confirmar), o pagamento já
registrado não é duplicado.

**Quais características da arquitetura permitem que apenas esse serviço seja escalado independentemente?**
- **Comunicação assíncrona via fila:** o produtor não sabe quantos consumidores existem; novas instâncias apenas se
  inscrevem na mesma fila.
- **Serviço sem estado:** nenhuma instância guarda informação em memória entre mensagens; o estado fica no banco do
  Pagamento, compartilhado pelas instâncias.
- **Banco por serviço:** escalar o Pagamento não exige nenhuma mudança no Pedido, no Estoque ou nos bancos deles.
- **Containers idênticos e descartáveis:** todas as instâncias usam a mesma imagem e configuração.
- **Sem porta exposta no host:** o Pagamento é um worker, então as réplicas não disputam a mesma porta.
- **Confirmação de mensagens e idempotência:** garantem que a divisão do trabalho entre instâncias não perca nem
  duplique pagamentos.

**Em quais circunstâncias o Estoque Service também precisaria ser escalado?**
Quando ele se tornasse o gargalo do sistema, por exemplo:
- **Alto volume de pedidos:** toda criação de pedido faz uma chamada síncrona ao Estoque. Se ele ficar lento, o cliente
  espera mais; se ficar indisponível, nenhum pedido é criado. Escalar o Pagamento não resolve isso, pois o Estoque está
  no caminho síncrono da requisição.
- **Muitas consultas ao catálogo:** grande número de acessos à listagem e à consulta de produtos (ex.: datas
  promocionais), mesmo sem geração de pedidos.
- **Muitas compensações:** um volume alto de pagamentos rejeitados gera muitas liberações de estoque.
- **Tempo de resposta ou uso de recursos acima do aceitável** nas instâncias atuais.

Nesse caso, seria necessário um balanceador de carga na frente das instâncias. A partir de certo ponto, o gargalo passa
a ser o próprio banco do Estoque, que pode exigir réplicas de leitura ou cache para as consultas.

---

## Etapa 11 — Observabilidade: investigação do incidente do Pedido #17

O Pedido Service gera um `correlationId` único para cada requisição e o propaga para o Estoque (no cabeçalho da
requisição), para a mensagem publicada no RabbitMQ e para o Pagamento. Como os três serviços registram esse
identificador em todos os logs, filtrar os logs pelo `correlationId` do pedido reconstrói o caminho completo da
requisição entre os serviços.

**1. O pedido foi criado?**
Sim. A consulta ao pedido o retorna com status `AGUARDANDO_PAGAMENTO`, e o log do Pedido Service registra a criação do
pedido com o seu `correlationId`.

**2. O estoque foi reservado?**
Sim. O log do Estoque Service registra a reserva do produto com o mesmo `correlationId`. Se a reserva tivesse falhado,
o pedido nem teria sido criado.

**3. O evento pedido.criado foi publicado?**
Sim. O log do Pedido Service registra a publicação do evento. A mensagem pode ser vista na fila `pedido.criado` com o
mesmo `correlationId`.

**4. O Pagamento Service recebeu o evento?**
Não. O Pagamento Service estava indisponível no momento em que o pedido foi criado. O evento chegou à fila
`pedido.criado`, mas não havia nenhum consumidor conectado para recebê-lo, e o log do Pagamento não tem nenhum registro
de recebimento com o `correlationId` do pedido.

**5. O pagamento foi processado?**
Não. Não existe registro de pagamento para o pedido no banco do Pagamento, nenhum log de aprovação ou rejeição e
nenhum evento `pagamento.processado`. Por isso o pedido permaneceu em `AGUARDANDO_PAGAMENTO`.

**6. Em qual etapa ocorreu o problema?**
No consumo do evento pelo Pagamento Service, que estava fora do ar. Criação do pedido, reserva de estoque e publicação
no RabbitMQ funcionaram corretamente; o fluxo parou entre a publicação do evento e o seu recebimento.

**7. Qual evidência nos logs permite identificar a etapa da falha?**
Filtrando os logs dos três serviços pelo `correlationId`, a sequência mostra a criação do pedido (Pedido Service), a
reserva do produto (Estoque Service) e a publicação do evento (Pedido Service). Depois disso, não há nenhuma linha do
Pagamento Service com esse `correlationId`. O log do Pagamento mostra que o serviço foi encerrado antes da criação do
pedido e não registra nenhuma atividade até ser religado. A ausência do recebimento do evento, do log de aprovação ou
rejeição e da atualização do status do pedido identifica que o fluxo parou na entrega ao Pagamento.

**8. O que aconteceu com a mensagem no RabbitMQ?**
Ela não foi perdida. A mensagem permaneceu armazenada na fila `pedido.criado`, como mensagem pronta para entrega e
sem consumidor conectado, persistida pelo RabbitMQ. Quando o Pagamento Service foi religado, ele se conectou à fila,
recebeu a mensagem pendente e processou o pagamento automaticamente, sem intervenção manual. Após a confirmação do
processamento, a mensagem foi removida da fila e o pedido teve seu status atualizado.

---

## Etapa 12 — Atualização assíncrona do pedido

Após processar o pagamento, o Pagamento Service publica o evento `pagamento.processado` com o identificador do pedido,
o resultado (`APROVADO` ou `REJEITADO`) e o `correlationId`. O Pedido Service consome esse evento e atualiza o status no
seu próprio banco: `APROVADO` resulta em `PAGO`, e `REJEITADO` resulta em `REJEITADO`, com a devolução do estoque
reservado. O Pagamento Service nunca acessa o banco do Pedido Service.
