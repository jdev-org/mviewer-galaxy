FROM ubuntu:24.04

ENV container=docker

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
       systemd systemd-sysv dbus openssh-server sudo python3 ca-certificates \
    && useradd --create-home --shell /bin/bash deploy \
    && usermod --password '*' deploy \
    && printf 'deploy ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/deploy \
    && chmod 0440 /etc/sudoers.d/deploy \
    && install -d -m 0700 -o deploy -g deploy /home/deploy/.ssh \
    && systemctl disable ssh.socket \
    && systemctl enable ssh.service \
    && systemctl mask systemd-udevd.service \
       systemd-udevd-control.socket systemd-udevd-kernel.socket \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 22 80

# nginx sera installé par Ansible ; préparer le relais HTTP interne du test.
COPY nginx-localhost.conf /etc/nginx/conf.d/ansible-test-localhost.conf

STOPSIGNAL SIGRTMIN+3

CMD ["/sbin/init"]
