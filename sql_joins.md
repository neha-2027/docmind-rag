# SQL joins

A join combines rows from two tables based on a related column. An INNER JOIN returns only the rows that have matching values in both tables. A LEFT JOIN returns every row from the left table and the matching rows from the right table; when there is no match, the right side columns are NULL.

A RIGHT JOIN is the mirror image of a LEFT JOIN. A FULL OUTER JOIN returns all rows from both tables, with NULL where there is no match.

A primary key uniquely identifies each row in a table. A foreign key is a column that references the primary key of another table, which is how relationships such as users and their orders are modelled.

Indexes speed up lookups on columns used in WHERE clauses and joins, but they slow down inserts and updates slightly because the index must be maintained.
