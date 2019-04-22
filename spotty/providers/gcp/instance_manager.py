from spotty.commands.writers.abstract_output_writrer import AbstractOutputWriter
from spotty.errors.instance_not_running import InstanceNotRunningError
from spotty.providers.abstract_instance_manager import AbstractInstanceManager
from spotty.providers.gcp.config.instance_config import InstanceConfig
from spotty.providers.gcp.deployment.image_deployment import ImageDeployment
from spotty.providers.gcp.deployment.instance_deployment import InstanceDeployment
from spotty.providers.gcp.errors.image_not_found import ImageNotFoundError


class InstanceManager(AbstractInstanceManager):

    @property
    def instance_deployment(self) -> InstanceDeployment:
        """Returns an instance deployment manager."""
        return InstanceDeployment(self.project_config.project_name, self.instance_config)

    @property
    def image_deployment(self) -> ImageDeployment:
        """Returns an image deployment manager."""
        raise NotImplementedError

    def _get_instance_config(self, config: dict) -> InstanceConfig:
        return InstanceConfig(config)

    @property
    def instance_config(self) -> InstanceConfig:
        """This property is redefined just for a correct type hinting."""
        return self._instance_config

    def is_running(self):
        return bool(self.instance_deployment.get_instance())

    def start(self, output: AbstractOutputWriter, dry_run=False):
        deployment = self.instance_deployment

        if not dry_run:
            # check if the instance is already running
            instance = deployment.get_instance()
            if instance:
                print('Instance is already running. Are you sure you want to restart it?')
                res = input('Type "y" to confirm: ')
                if res != 'y':
                    raise ValueError('The operation was cancelled.')

                # terminating the instance to make EBS volumes available
                output.write('Terminating the instance...')
                instance.terminate()
                instance.wait_instance_terminated()

            # check that the AMI exists
            if not deployment.get_image():
                print('The image "%s" doesn\'t exist. Do you want to create it?'
                      % self.instance_config.image_name)
                res = input('Type "y" to confirm: ')
                if res == 'y':
                    # create an image
                    self.image_deployment.deploy(False, output)
                    output.write()
                else:
                    raise ImageNotFoundError(self.instance_config.image_name)

        # deploy the instance
        deployment.deploy(self.project_config, output, dry_run=dry_run)

    def stop(self, output: AbstractOutputWriter):
        self.instance_deployment.stack.delete_stack(output)

    def sync(self, output: AbstractOutputWriter, dry_run=False):
        raise NotImplementedError

    def download(self, download_filters: list, output: AbstractOutputWriter, dry_run=False):
        raise NotImplementedError

    def clean(self, output: AbstractOutputWriter):
        raise NotImplementedError

    def get_status_text(self) -> str:
        return ''

    def get_public_ip_address(self) -> str:
        """Returns a public IP address of the running instance."""
        instance = self.instance_deployment.get_instance()
        if not instance:
            raise InstanceNotRunningError(self.instance_config.name)

        return instance.public_ip_address

    @property
    def ssh_user(self):
        return 'ubuntu'

    @property
    def ssh_key_path(self):
        raise NotImplementedError
