from fabric import colors
import os, time, boto
import ConfigParser
import boto.ec2
from fabric.contrib.files import exists

__author__ = 'schien'

from fabric.api import *

GIT_ORIGIN = "git@github.com"

# The git repo is the repo we should clone
GIT_REPO = "dschien/ep_site.git"

# env.hosts = ['52.18.118.168']

# The hosts we need to configure
# HOSTS = ["ec2-52-17-239-200.eu-west-1.compute.amazonaws.com"]


CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.forward_agent = True
env.hosts = [config.get('ec2', 'host')]

# from django.utils.crypto import get_random_string
# chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
secret_key = config.get('django', 'secret_key')


#### Environments

def production():
    "Setup production settings"
    # check_or_start_instance()
    env.repo = ("ep-venv", "origin", "release")
    env.virtualenv, env.parent, env.branch = env.repo
    env.base = "/opt"
    env.user = "ubuntu"
    env.git_origin = GIT_ORIGIN
    env.git_repo = GIT_REPO
    env.dev_mode = False
    env.key_filename = '~/.ssh/oracle_rsa'
    env.forward_agent = True


def test():
    run('sudo apt-get update')


def sub_git_clone():
    """
    Clones a repository into the virtualenv at /project

    :return:
    """
    print colors.cyan('Clone repo...')
    run(
        "git clone %(git_origin)s:%(git_repo)s" % env)


def install_make_tools():
    run('sudo apt-get update')
    run('sudo apt-get -y install build-essential')


def install_py35():
    run('sudo add-apt-repository ppa:fkrull/deadsnakes')
    run('sudo apt-get update')
    run('sudo apt-get -y install python3.5')
    run('sudo apt-get -y install python3.5-venv')
    run('sudo apt-get -y install python3.5-dev')
    run('sudo apt-get -y install libfreetype6-dev')
    run('sudo apt-get -y install libxft-dev')
    run('sudo apt-get -y install libpq-dev')
    run('sudo apt-get -y install lib32ncurses5-dev')
    run('sudo apt-get -y install git')
    run('sudo apt-get -y install supervisor')
    run('echo -e "Host github.com\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config')


def install_webstack():
    run('sudo apt-get -y install nginx')
    run('sudo mkdir /etc/nginx/ssl')
    run(
        'sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt -subj "/C=UK/ST=Avon/L=Bristol/O=UoB/OU=CS/CN=cs.bris.ac.uk"')

    run('sudo service nginx restart')
    run('sudo update-rc.d nginx defaults')


def config_webstack():
    run('sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.old')
    run('sudo cp ep_site/etc_services_conf/nginx.conf /etc/nginx/nginx.conf')
    run('sudo chown root:root /etc/nginx/nginx.conf')
    run('sudo cp ep_site/etc_services_conf/nginx-app-proxy.conf /etc/nginx/sites-available/')
    if exists('/etc/nginx/sites-enabled/default'):
        run('sudo rm /etc/nginx/sites-enabled/default')
    if not exists('/etc/nginx/sites-enabled/nginx-app-proxy.conf'):
        run(
            'sudo ln -s /etc/nginx/sites-available/nginx-app-proxy.conf /etc/nginx/sites-enabled/nginx-app-proxy.conf' % env)
    run('sudo chown root:root /etc/nginx/sites-available/nginx-app-proxy.conf')
    # gunicorn
    if not exists('/var/log/gunicorn/'):
        run('sudo mkdir /var/log/gunicorn/')

    if not exists('ep_site/log/'):
        run('sudo mkdir ep_site/log/')

    if not exists('ep_site/log/gunicorn'):
        run('sudo mkdir ep_site/log/gunicorn')

    run('sudo cp ep_site/etc_services_conf/gunicorn-supervisord.conf /etc/supervisor/conf.d/gunicorn-supervisord.conf')
    run('sudo cp ep_site/etc_services_conf/supervisord-init /etc/init.d/supervisord')
    run('sudo chmod +x /etc/init.d/supervisord')
    run('sudo update-rc.d supervisord defaults')


def django_deploy():
    with prefix('source ep-venv/bin/activate'):
        # with cd('ep_site'):
        run('sudo touch ep_site/log/ep.log')
        run('sudo chown -R ubuntu ep_site/log')
        run('cp ep_site/ep_site/local_settings.template.py ep_site/ep_site/local_settings.py')
        print secret_key
        run('sed -i -e "s/INSERT_SECRET_KEY/%(secret_key)s/g" ep_site/ep_site/local_settings.py' % {
            'secret_key': secret_key})


def django_update_actions():
    with prefix('source ep-venv/bin/activate'):
        run('python ep_site/manage.py collectstatic -v 0 --noinput')
        run('python ep_site/manage.py migrate')


def install_numpy():
    with prefix('source ep-venv/bin/activate'):
        run('pip install "ipython[notebook]"')


def update():
    with cd('ep_site'):
        run('git pull')


def clone_git():
    with cd('/opt'):
        run('git ')


def deploy():
    install_make_tools()
    install_py35()
    install_rabbit()
    clone_git()
    install_py_deps()


def install_rabbit():
    run('sudo apt-get -y install rabbitmq-server')


def create_virtualenv():
    run('pyvenv-3.5 ep-venv')


def install_py_deps():
    with prefix('source ep-venv/bin/activate'):
        run('pip install -r requirements.txt')


# def copy_projects():
#     with cd('coms20805'):
#         run('git pull')
#         run('cp -R client_projects_2015/ /home/web/HTML/Teaching/Resources/COMS20805')


def sub_get_requirements():
    "Gets the requirements for the project"
    sudo("cd %(base)s/%(virtualenv)s; source bin/activate; pip install -r project/requirements.txt" % env)


def get_own_ip():
    from urllib import urlopen
    import re

    data = str(urlopen('http://checkip.dyndns.com/').read())
    # data = '<html><head><title>Current IP Check</title></head><body>Current IP Address: 65.96.168.198</body></html>\r\n'

    return re.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(data).group(1)
