CREATE TABLE produto (
    id BIGINT PRIMARY KEY,
    nome VARCHAR(100),
    quantidade INTEGER
);

INSERT INTO produto (id, nome, quantidade) VALUES
    (1, 'Notebook', 10),
    (2, 'Mouse', 50),
    (3, 'Teclado', 20);
