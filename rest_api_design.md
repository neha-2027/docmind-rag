# REST API design

REST APIs expose resources through URLs and use HTTP methods to describe actions. GET reads a resource, POST creates one, PUT replaces a resource completely, PATCH changes only some fields, and DELETE removes it.

Status codes tell the client what happened. 200 means success, 201 means a resource was created, 204 means success with no response body, 400 means the request was invalid, 401 means the client is not authenticated, 404 means the resource was not found, and 500 means a server error.

Good APIs validate input and return clear error messages. Large collections should be paginated using parameters such as page and per_page so that responses stay small.

Authentication is often done with bearer tokens sent in the Authorization header. Passwords must never be stored in plain text; they are stored as salted hashes.
