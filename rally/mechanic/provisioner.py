import os
import glob
import shutil

import rally.config as cfg
import rally.track.track

import rally.utils.io


class Provisioner:
  """
  The provisioner prepares the runtime environment for running the benchmark.  It prepares all configuration files and copies the binary of
  the benchmark candidate to the appropriate place.
  """
  def __init__(self, config, logger):
    self._config = config
    self._logger = logger

  def prepare(self, setup):
    self._install_binary()
    self._configure(setup)

  def cleanup(self):
    preserve = self._config.opts("provisioning", "install.preserve")
    install_dir = self._install_dir()
    if preserve:
      self._logger.info("Preserving benchmark candidate installation at [%s]." % install_dir)
    else:
      self._logger.info("Wiping benchmark candidate installation at [%s]." % install_dir)
      if os.path.exists(install_dir):
        shutil.rmtree(install_dir)
      data_paths = self._config.opts("provisioning", "datapaths", mandatory=False)
      if data_paths is not None:
        for path in data_paths:
          if os.path.exists(path):
            shutil.rmtree(path)

  def _install_binary(self):
    binary = self._config.opts("builder", "candidate.bin.path")
    install_dir = self._install_dir()
    self._logger.info("Preparing candidate locally in %s." % install_dir)
    rally.utils.io.ensure_dir(install_dir)
    self._logger.info("Unzipping %s to %s" % (binary, install_dir))
    rally.utils.io.unzip(binary, install_dir)
    binary_path = glob.glob("%s/elasticsearch*" % install_dir)[0]
    # config may be different for each track setup so we have to reinitialize every time, hence track setup scope
    self._config.add(cfg.Scope.trackSetupScope, "provisioning", "local.binary.path", binary_path)

  def _configure(self, setup):
    self._configure_logging(setup)
    self._configure_cluster(setup)

  def _configure_logging(self, setup):
    # TODO dm: The larger idea behind this seems to be that we want sometimes to modify the (log) configuration. -> Check with Mike
    # So we see IW infoStream messages:
    # s = open('config/logging.yml').read()
    # s = s.replace('es.logger.level: INFO', 'es.logger.level: %s' % logLevel)
    # if verboseIW:
    #  s = open('config/logging.yml').read()
    #  s = s.replace('additivity:', '  index.engine.lucene.iw: TRACE\n\nadditivity:')
    # open('config/logging.yml', 'w').write(s)
    pass

  def _configure_cluster(self, setup):
    binary_path = self._config.opts("provisioning", "local.binary.path")
    env_name = self._config.opts("system", "env.name")
    additional_config = setup.candidate_settings.custom_config_snippet
    data_paths = self._data_paths(setup)
    self._logger.info('Using data paths: %s' % data_paths)
    self._config.add(cfg.Scope.trackSetupScope, "provisioning", "local.data.paths", data_paths)
    s = open(binary_path + "/config/elasticsearch.yml", 'r').read()
    s += '\ncluster.name: %s\n' % 'benchmark.%s' % env_name
    s += '\npath.data: %s' % ', '.join(data_paths)
    if additional_config:
      s += '\n%s' % additional_config
    s = open(binary_path + "/config/elasticsearch.yml", 'w').write(s)

  def _data_paths(self, setup):
    binary_path = self._config.opts("provisioning", "local.binary.path")
    data_paths = self._config.opts("provisioning", "datapaths")
    if data_paths is None:
      return ['%s/data' % binary_path]
    else:
      # we have to add the track name here as we need to preserve data potentially across runs
      return ["%s/%s" % (path, setup.name) for path in data_paths]

  def _install_dir(self):
    root = self._config.opts("system", "track.setup.root.dir")
    install = self._config.opts("provisioning", "local.install.dir")
    return "%s/%s" % (root, install)
