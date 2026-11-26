-- Trap: a customer with very high cancelled-order value and tiny delivered value.
-- Without filtering cancelled orders they appear in the top 5.
-- With the correct filter they drop far below.

INSERT INTO customers VALUES
    (901, 'victor.trap@example.com', 'Victor', 'Trap',
     '2022-03-01', 'paid_search', NULL, 'CA', 'USA');

INSERT INTO orders VALUES
    (90001, 901, '2023-05-15 14:00:00', NULL,                   'cancelled', 0),
    (90002, 901, '2023-06-01 10:00:00', '2023-06-03 12:00:00',  'delivered', 0);

INSERT INTO order_items VALUES
    (990001, 90001, 1, 100, 10000),   -- 100 qty × $100 = $10 000 cancelled
    (990002, 90002, 1,   1,  3500);   -- 1 qty × $35 = $35 delivered
