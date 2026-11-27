# AWS basics

Amazon S3 is object storage. Data is stored in buckets as objects, and each object is addressed by a key. S3 is commonly used for backups, static files and data lakes.

AWS Lambda runs code without managing servers. A function is triggered by an event, such as a file upload to S3 or an HTTP request, and the customer pays only for the compute time used.

IAM controls who can do what in an AWS account. Users, roles and policies follow the principle of least privilege, which means granting only the permissions that are really needed. Applications running on AWS should use IAM roles instead of hard-coded access keys.

Amazon EC2 provides virtual servers. Amazon CloudWatch collects logs and metrics so that engineers can monitor applications and set alarms.
