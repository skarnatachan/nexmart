# Deploying Django to AWS Elastic Beanstalk

Guidelines and checklist, based on deploying NexMart (Django + RDS PostgreSQL + S3 media + SQS/Celery).

## 1. Preparation checklist

### AWS account and tools
- [ ] Create an IAM user for the CLI (access key type "CLI"). Prefer IAM Identity Center (SSO) over long-lived keys. Give it `AdministratorAccess-AWSElasticBeanstalk` plus the S3 and RDS access you need. Never use root keys.
- [ ] Run `aws configure` **in your own terminal** with region = your target region. Verify with `aws sts get-caller-identity`.
- [ ] Install the EB CLI (`brew install awsebcli`).
- [ ] Pick one region and use it everywhere (RDS, S3, EB, SQS).

### App readiness
- [ ] `gunicorn`, `whitenoise`, a Postgres driver (`psycopg[binary]`), `django-storages`, `boto3` and `django-environ` are in `requirements.txt`.
- [ ] Settings read everything from environment variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, database, email, API keys.
- [ ] `ALLOWED_HOSTS` allows `.elasticbeanstalk.com` and your domain.
- [ ] Static files use WhiteNoise, with `STATIC_ROOT` set.
- [ ] Add a lightweight `/health/` URL that doesn't touch the database.
- [ ] Add console `LOGGING`, or production errors will be invisible.
- [ ] **Test against Postgres locally**, not only sqlite. sqlite ignores field lengths, which caused our add-to-cart 500.
- [ ] Run `python manage.py check --deploy` with `DEBUG=False`.

### Data and services
- [ ] RDS PostgreSQL instance in the same region (a private network is best).
- [ ] S3 bucket for user-uploaded media, with a bucket policy limited to `media/*`.
- [ ] If you use Celery, pick a broker (SQS is cheapest and needs no server). Elastic Beanstalk instances have no Redis.
- [ ] A domain name if you want HTTPS (ACM certificates need one).
- [ ] Keep `.env` out of git and out of the deploy bundle.

## 2. Project files

**`Procfile`**
```
web: gunicorn myproject.wsgi:application --bind 127.0.0.1:8000 --workers 3
celery: celery -A myproject worker --loglevel=info
```

**`.ebextensions/01_django.config`**
```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    DJANGO_SETTINGS_MODULE: myproject.settings
    DEBUG: "False"
  aws:elasticbeanstalk:environment:process:default:
    HealthCheckPath: /health/
container_commands:
  01_migrate:
    command: "source /var/app/venv/*/bin/activate && python manage.py migrate --noinput"
    leader_only: true
  02_collectstatic:
    command: "source /var/app/venv/*/bin/activate && python manage.py collectstatic --noinput"
```

**`.ebignore`** is used instead of `.gitignore` when present. Exclude `.git`, `.venv`, `node_modules`, `.env`, `db.sqlite3`, `media/`, `staticfiles/`, and `.elasticbeanstalk/`.

**`.platform/nginx/conf.d/uploads.conf`**: `client_max_body_size 10M;` (the nginx default is 1 MB, which breaks image uploads).

## 3. Deployment steps

1. **IAM roles** (once per account):
   - A service role `aws-elasticbeanstalk-service-role` with `AWSElasticBeanstalkEnhancedHealth` and `AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy`.
   - An instance role `aws-elasticbeanstalk-ec2-role` with `AWSElasticBeanstalkWebTier` and `WorkerTier`, plus an inline policy granting S3 access to `media/*` and SQS access to `yourapp-*` queues. Create an instance profile with the same name.
   - This lets the app use **no access keys** at runtime.
2. `eb init` (app name, region, platform: Python 3.13 on Amazon Linux 2023).
3. `eb create <env> --single --instance_type t3.small --instance_profile … --service-role … --envvars "KEY=val,…"`. Use `--single` for a cheap setup, or omit it for a load balancer.
4. Open the RDS security group for the instance's public IP on port 5432. (If RDS is in the same VPC, allow the EB security group instead.)
5. Verify `/health/`, a page that reads the database, an image from S3, and a state-changing action like add-to-cart.
6. Later updates: commit, then `eb deploy`.

## 4. Production hardening

- **HTTPS:** domain, then ACM certificate, then load balancer with a 443 listener. Then set `USE_HTTPS=True`, `CSRF_TRUSTED_ORIGINS` and a restricted `ALLOWED_HOSTS`. `SECURE_PROXY_SSL_HEADER` is required behind the load balancer.
- **Database:** use `sslmode=require`, a strong password, and a security group scoped to your IPs. Make it private if you can.
- **Secrets:** set them with `eb setenv`, or use Secrets Manager. Never put them in the repo.
- **Backups:** enable RDS automated backups and snapshots.
- **Monitoring:** CloudWatch alarms on health and 5xx errors, and Sentry if you want tracebacks pushed to you.
- **Cost:** stop or delete unused environments and old RDS instances.

## 5. Pitfalls we hit

| Symptom | Cause | Fix |
|---|---|---|
| `migrate` times out | RDS not publicly reachable or security group closed | Set Public access = Yes or use a VPC route, and add your IP to the security group |
| `collectstatic` fails on `@import "tailwindcss"` | Source CSS gets post-processed by the manifest storage | Use `--ignore input.css` |
| 500 on add-to-cart, `varchar(2)` | Model field too short; sqlite doesn't enforce lengths | Test on Postgres, widen the field |
| 500 with no traceback | No `LOGGING` config with `DEBUG=False` | Log to the console |
| `eb deploy` fails with an invalid YAML error | Hand-edited `.ebextensions` | Validate with `ruby -ryaml` before deploying |
| Local commands fail after IP change | RDS security group has your old IP | Re-add your current IP |
| Migrations missing on deploy | `*/migrations/` is gitignored | `.ebignore` ships them, or track them in git |
| Celery emails never send | No broker on the instance | SQS or ElastiCache |
| `eb logs` returns 403 | Log-bundle bucket permission quirk | Use `request-environment-info` and `aws s3 cp` |

## 6. Debugging toolbox

- `eb status`, `eb events`, `eb health`
- `eb logs` (or the API route above): check `web.stdout.log`, `eb-engine.log` and `cfn-init-cmd.log`
- `eb ssh` for the instance, with logs in `/var/log/` and the app in `/var/app/current`
- `eb printenv` to confirm environment variables
