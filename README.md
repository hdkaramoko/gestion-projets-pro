# Project Pilot

Project Pilot est un cockpit personnel permettant de piloter ses projets,
actions, réunions et échéances. Le projet est construit progressivement selon
le plan décrit dans `prompts/initialisation-app.md`.

## État actuel

Les étapes 1 à 7 fournissent le socle Django, l'authentification par email ainsi
que la gestion sécurisée des projets, macro-activités, tâches, captures et
réunions. Les captures et actions de réunion peuvent être transformées une seule
fois en tâches, avec conservation de leur origine. Le tableau de bord centralise
les actions quotidiennes, alertes, échéances et indicateurs utiles. Le calendrier
FullCalendar regroupe les planifications, échéances et réunions.

## Démarrage local

Prérequis : Python 3.13 et `uv`.

```bash
uv sync
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Sous PowerShell, utiliser `Copy-Item .env.example .env`.

## Qualité

```bash
uv run python manage.py test
uv run ruff check .
uv run ruff format .
```

SQLite reste la base utilisée par défaut en local. Pour utiliser PostgreSQL sur
le SSP Cloud, définir `DB_ENGINE=postgresql` et renseigner toutes les variables
`POSTGRES_*` documentées dans `.env.example`.

## Déploiement SSP Cloud

Les migrations et la collecte des fichiers statiques sont des étapes explicites,
séparées du démarrage Gunicorn :

```bash
uv run python manage.py migrate --noinput
uv run python manage.py collectstatic --noinput
uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
```

Dans Kubernetes, un conteneur d'initialisation exécute les migrations avant le
démarrage de l'application. Si une migration échoue, le pod applicatif ne
démarre pas. Aucun secret n'est intégré à l'image Docker.
