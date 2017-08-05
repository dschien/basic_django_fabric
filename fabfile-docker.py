import ConfigParser
import logging

from fabric.api import *

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.forward_agent = True
env.update(config._sections['ep_common'])


def prod():
    env.update(config._sections['django'])


def update():
    with cd('ep_site'):
        run('git pull --recurse-submodules')
        run('git submodule init')
        run('git submodule update')
        # run('git submodule foreach git pull origin master')


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

container_state = {'RUNNING': 1, 'STOPPED': 2, 'NOT_FOUND': 3}


# docker inspect --format="{{ .State.StartedAt }}" $CONTAINER)
# NETWORK=$(docker inspect --format="{{ .NetworkSettings.IPAddress }}" $CONTAINER
def inspect_container(container_name_or_id=''):
    """ e.g. fab --host ep.iodicus.net inspect_container:container_name_or_id=... """
    with settings(warn_only=True):
        result = run("docker inspect --format '{{ .State.Running }}' " + container_name_or_id)
        running = (result == 'true')
    if result.failed:
        logger.warn('inspect_container failed for container {}'.format(container_name_or_id))
        return container_state['NOT_FOUND']
    if not running:
        logger.info('container {} stopped'.format(container_name_or_id))
        return container_state['STOPPED']
    logger.info('container {} running'.format(container_name_or_id))
    return container_state['RUNNING']



    # container_started_at = run("docker inspect --format '{{ .State.StartedAt }}' " + container_name_or_id)
    # container_IP = run("docker inspect --format '{{ .NetworkSettings.IPAddress }}' " + container_name_or_id)
    #


def stop_container(container_name_or_id=''):
    with settings(warn_only=True):
        result = run("docker stop " + container_name_or_id)
        if not result.failed:
            logger.info('container {} stopped'.format(container_name_or_id))


def remove_container(container_name_or_id=''):
    with settings(warn_only=True):
        result = run("docker rm " + container_name_or_id)
        if result == container_name_or_id:
            logger.info('container {} removed'.format(container_name_or_id))
        else:
            logger.warn('unexpect command result, check log output')


def docker_logs(container_name_or_id=''):
    with settings(warn_only=True):
        run('docker logs --tail 50 -f {}'.format(container_name_or_id))


# @todo - parameterise container name
def start_container():
    with settings(warn_only=True):
        with cd(''):
            result = run(
                'docker run -h %(sys_type)s --name %(container_name) -e "C_FORCE_ROOT=true" -p %(source_port):%(dest_port) -d -v `pwd`:/%(mount_dest) -w /%(mount_dest) %(docker_container_name) %(container_command)' % env
            )
            if not result.failed:
                logger.info('container %(container_name) started' % env)


def redeploy_container(container_name_or_id=''):
    """ e.g. fab --host ep.iodicus.net inspect_container:container_name_or_id=... """
    state = inspect_container(container_name_or_id)
    if state == container_state['RUNNING']:
        stop_container(container_name_or_id)
    remove_container(container_name_or_id)
    # @todo - parameterise container name
    if container_name_or_id == 'web':
        start_container()


def update_site(pull=True):
    """
    Pull from git and restart docker containers
    :return:
    """
    if pull:
        update()
    restart_containers()


def restart_containers():
    for container in ['django', ]:
        stop_container(container)

    # for container in ['rabbit', 'memcache']:
    #     redeploy_container(container)

    for container in ['web', 'celery_worker', 'celery_beat']:
        redeploy_container(container)


def initial_container_deployment():
    run('docker create -v /var/lib/rabbitmq --name celery_rabbit_data busybox')
