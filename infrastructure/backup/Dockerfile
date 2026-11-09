FROM postgres:16-alpine
RUN apk add --no-cache age bash coreutils findutils
COPY backup.sh restore.sh verify.sh entrypoint.sh /opt/backup/
RUN chmod +x /opt/backup/*.sh
ENTRYPOINT ["/opt/backup/entrypoint.sh"]
