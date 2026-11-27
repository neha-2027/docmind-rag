# Flask basics

Flask is a lightweight Python web framework. A Flask application is created by calling the Flask class with the module name. Routes are attached to view functions using the route decorator, and each route can accept specific HTTP methods such as GET and POST.

Flask has no built-in database layer or form validation, so developers add these themselves. Request data is read from the request object, for example request.get_json for JSON bodies. Responses are usually built with jsonify, which sets the correct content type.

The application factory pattern wraps app creation inside a function called create_app. This makes testing easier because every test can build a fresh application with its own configuration, such as a temporary database file.

Blueprints split a large Flask application into smaller modules. Each blueprint groups related routes and is registered on the main app.
