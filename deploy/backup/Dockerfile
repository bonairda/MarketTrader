FROM postgres:16-alpine

RUN apk add --no-cache bash coreutils rclone tzdata

COPY backup.sh restore.sh verify-backup.sh backup-loop.sh /opt/markettracker/
RUN chmod +x /opt/markettracker/*.sh

VOLUME ["/backups"]

CMD ["/opt/markettracker/backup-loop.sh"]
