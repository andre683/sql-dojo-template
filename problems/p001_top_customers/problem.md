# p001 · Top 5 Customers by Net Revenue

**Difficulty:** easy  
**Concepts:** aggregation, join, filter  
**Tables:** customers, orders, order_items

---

The marketing team wants to invite the top 5 customers to an exclusive VIP tasting event.
A customer's **net revenue** is the total value of all orders that were not cancelled or refunded.

**Write a query that returns the top 5 customers ranked by net revenue.**

Output columns (exact names required):

| column               | type    | notes                              |
|----------------------|---------|------------------------------------|
| customer_id          | integer |                                    |
| full_name            | varchar | first_name \|\| ' ' \|\| last_name |
| total_revenue_cents  | bigint  | SUM of quantity × unit_price_cents |
| order_count          | bigint  | number of qualifying orders        |

Order by `total_revenue_cents` descending.

---

**Before you write SQL:** what does one row in your output represent?
