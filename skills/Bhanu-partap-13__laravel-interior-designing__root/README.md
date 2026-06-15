# Interior Project (Laravel)

This repository contains a Laravel-based interior design project platform used for showcasing designers, projects, and handling client inquiries.

**Purpose:** Local development and testing of the interior design application and its services (mail, broadcasting, database).

**Primary contact:** repository owner

**Important files:** [docker-compose.yml](docker-compose.yml), [Dockerfile](Dockerfile), [.env](.env), [app/Http/Controllers/InquiryController.php](app/Http/Controllers/InquiryController.php#L1-L200)

---

**Tech Stack**

- **Framework:** Laravel (PHP)
- **PHP runtime:** PHP 8.3
- **Database:** MySQL 8 (containerized)
- **Frontend build:** Node 20 + Vite + Tailwind CSS
- **Queue/Broadcasting:** laravel/reverb (local Reverb server) or log driver for dev
- **Mail:** SMTP (configurable), recommended to use `log` during local development
- **Docker:** Docker + Docker Compose to run app, db, reverb, phpmyadmin

---

**Prerequisites (local dev machine)**

- Docker and Docker Compose
- Git
- (optional) PHP, Composer and Node.js if you want to run outside Docker

---

**Quick start (Docker)**

1. Copy the environment file:

	`cp .env.example .env` (or create `.env` from repo `.env` template)

2. Edit `.env` and set values for DB, MAIL, REVERB if necessary. See the Environment section below.

3. Build and start containers:

	`docker compose up -d --build`

4. Run migrations and seeders (inside the `app` container):

	`docker compose exec app php artisan migrate --force`
	`docker compose exec app php artisan db:seed --force`

5. Visit the app in your browser: `http://localhost:10000`

6. Admin tools:

	- phpMyAdmin: `http://localhost:8081`
	- Reverb (if enabled): `http://localhost:8082`

---

**Environment / .env (key values to check)**

- `APP_ENV`, `APP_KEY`, `APP_URL`
- `DB_CONNECTION`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`
- `SESSION_DRIVER` (`database` or `file`) — if using `database`, ensure sessions table exists (`php artisan session:table` + migrate)
- `MAIL_MAILER`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM_ADDRESS`
- `BROADCAST_CONNECTION` (e.g., `reverb` or `log`) and Reverb-related envs when using laravel/reverb

Tip: For quick local debugging set `MAIL_MAILER=log` so mail sends are written to `storage/logs/laravel.log` instead of failing due to SMTP connectivity.

---

**Common Commands**

- Build & start: `docker compose up -d --build`
- Stop: `docker compose down`
- Enter app container shell: `docker compose exec app sh`
- Run artisan commands: `docker compose exec app php artisan <command>`
- Install PHP deps (if running locally): `composer install`
- Install node deps & build (if running locally): `npm ci && npm run build`

---

**Development notes / gotchas**

- If you see HTTP 500 errors when forms are submitted, check `storage/logs/laravel.log` for exceptions. Common causes:
  - Database not reachable (ensure the `db` service is healthy; the Compose file includes a healthcheck).
  - Session driver set to `database` but `sessions` table missing.
  - Mail or broadcast failures — set `MAIL_MAILER=log` and `BROADCAST_CONNECTION=log` while debugging.

- The inquiry path (`POST /inquiries`) is implemented in [app/Http/Controllers/InquiryController.php](app/Http/Controllers/InquiryController.php#L1-L200). If sending a message triggers a 500, inspect mail and broadcast configuration first.

- If you modify Docker-related files, rebuild with `docker compose up -d --build`.

---

**Troubleshooting**

- DB connectivity errors (SQLSTATE[HY000] [2002]): ensure `DB_HOST` is `db` inside the `app` container and the `db` service is healthy. From host you may map ports (this repo maps host `3307` -> container `3306`).

- CSRF token mismatch on form submit: ensure pages include the CSRF meta tag and that the browser sends cookies. For API-style requests use `Accept: application/json` and a valid CSRF token.

- Session errors like `Session store not set on request.`: ensure session middleware runs and the session driver is configured correctly; if `database`, confirm the `sessions` table exists.

---

**Testing**

- Run PHPUnit inside the container:

  `docker compose exec app php artisan test`

---

**Contributing**

- Create feature branches from `main`.
- Follow PSR-12 PHP coding standards and run tests before opening PRs.

---

If you'd like, I can:

- Add a `.env.example` with recommended defaults.
- Add a CONTRIBUTING.md and DEVELOPMENT.md with more details.
- Update `docker-compose.yml` comments to document ports and services.

---

License: MIT

