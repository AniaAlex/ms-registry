FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /mnt/logs/
WORKDIR /app

# System deps (keep only what you need)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    postgresql-client \
    git && \
    rm -rf /var/lib/apt/lists/*

# Python deps
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt pyuwsgi

# Trim build deps
RUN apt-get --purge autoremove -y \
    build-essential \
    python3-dev

# uWSGI config
ADD uwsgi.ini /etc/uwsgi/app.ini

ADD ./rp_register /app

EXPOSE 3030 8000
CMD ["/usr/local/bin/uwsgi", "--ini", "/etc/uwsgi/app.ini"]
