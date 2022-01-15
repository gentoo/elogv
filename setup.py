ffrom distutils.core import setup
from distutils import log
from distutils.cmd import Command
from distutils.file_util import copy_file
from distutils.dir_util import remove_tree
from distutils.command.build import build as _build
from distutils.command.install import install as _install
from distutils.command.clean import clean as _clean

import os
from glob import glob

## Snippet of code found on
## http://developer.berlios.de/snippet/detail.php?type=snippet&id=100019
## Useful to handle *.po files under distutils


class messages(Command):

    description = 'Extract messages from source files'

    user_options = [('merge', 'm', 'Merge message catalogs after '
                     'extracting template')]

    boolean_options = ['merge']

    def initialize_options(self):
        self.merge = False

    def finalize_options(self):
        pass

    def run(self):
        wd = os.getcwd()
        name = self.distribution.get_name()
        log.info('Extracting messages from %s' % name)
        os.chdir('po')
        os.system('pygettext -k i18n -o %s.pot ../%s' % (name, name))
        os.chdir(wd)
        if self.merge:
            self.run_command('merge')


class merge(Command):
    description = 'Merge message catalogs with template'

    user_options = [('lang=', 'l', 'Only merge specified language')]

    def initialize_options(self):
        self.lang = None

    def finalize_options(self):
        pass

    def run(self):
        wd = os.getcwd()
        os.chdir('po')
        if self.lang is not None:
            filename = '%s.po' % self.lang
            if os.path.exists(filename):
                self.merge(filename)
            else:
                log.error('No catalog found for language %s' % self.lang)
        else:
            files = glob('*.po')
            for f in files:
                self.merge(f)
        os.chdir(wd)

    def merge(self, f):
        name = self.distribution.get_name()
        log.info('Merging catalog %s' % f)
        os.system('msgmerge %s %s.pot -o %s' % (f, name, f))


class build_messages(Command):

    description = 'Compile message catalogs'
    user_options = [('build-dir=', 'd',
                     'directory to build message catalogs in')]

    def initialize_options(self):
        self.build_dir = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_messages', 'build_dir'))

    def run(self):
        self.mkpath(self.build_dir)
        po_files = os.path.join('po', '*.po')
        po_files = glob(po_files)
        for f in po_files:
            base = os.path.basename(f)
            base = os.path.splitext(base)[0]
            out_file = os.path.join(self.build_dir, '%s.gmo' % base)
            log.info('Building catalog %s > %s' % (f, out_file))
            cmd = 'msgfmt -o "%s" %s' % (out_file, f)
            os.system(cmd)


class build(_build):
    # integrate build_message
    def has_messages(self):
        return True

    def initialize_options(self):
        _build.initialize_options(self)
        self.build_messages = None

    def finalize_options(self):
        _build.finalize_options(self)
        if self.build_messages is None:
            self.build_messages = os.path.join(self.build_base, 'po')

    _build.user_options.append(
        ('build-messages=', None, "build directory for messages"))
    _build.sub_commands.append(('build_messages', has_messages))


class install_messages(Command):

    description = 'Installs message catalogs'

    user_options = [
        ('install-dir=', 'd', "directory to install scripts to"),
        ('build-dir=', 'b', "build directory (where to install from)"),
        ('skip-build', None, "skip the build steps"),
    ]

    boolean_options = ['skip-build']

    def initialize_options(self):
        self.install_dir = None
        self.build_dir = None
        self.skip_build = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_messages', 'build_dir'))
        self.set_undefined_options(
            'install',
            ('install_data', 'install_dir'),
            ('force', 'force'),
            ('skip_build', 'skip_build'),
        )
        self.install_dir = os.path.join(self.install_dir, 'share', 'locale')

    def run(self):
        if not self.skip_build:
            self.run_command('build_messages')
        catalogs = glob(os.path.join(self.build_dir, '*.gmo'))
        for c in catalogs:
            base = os.path.basename(c)
            base = os.path.splitext(base)[0]
            out_dir = os.path.join(self.install_dir, base, 'LC_MESSAGES')
            self.mkpath(out_dir)
            out_file = os.path.join(out_dir,
                                    '%s.mo' % self.distribution.get_name())
            copy_file(c, out_file)


class clean(_clean):
    _clean.user_options.append(
        ('build-messages=', None,
         "build directory for messages (default: 'build.build-messages')"))

    def initialize_options(self):
        _clean.initialize_options(self)
        self.build_messages = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'),
                                   ('build_lib', 'build_lib'),
                                   ('build_scripts', 'build_scripts'),
                                   ('build_temp', 'build_temp'),
                                   ('build_messages', 'build_messages'))
        self.set_undefined_options('bdist', ('bdist_base', 'bdist_base'))

    def run(self):
        # remove the build/temp.<plat> directory (unless it's already
        # gone)
        if os.path.exists(self.build_temp):
            remove_tree(self.build_temp, dry_run=self.dry_run)
        else:
            log.debug("'%s' does not exist -- can't clean it", self.build_temp)

        if self.all:
            # remove build directories
            for directory in (self.build_lib, self.bdist_base,
                              self.build_scripts, self.build_messages):
                if os.path.exists(directory):
                    remove_tree(directory, dry_run=self.dry_run)
                else:
                    log.warn("'%s' does not exist -- can't clean it",
                             directory)

        # just for the heck of it, try to remove the base build directory:
        # we might have emptied it right now, but if not we don't care
        if not self.dry_run:
            try:
                os.rmdir(self.build_base)
                log.info("removing '%s'", self.build_base)
            except OSError:
                pass


## Class modified to add manpages command
class install(_install):
    def has_messages(self):
        return True

    def has_manpages(self):
        return True

    _install.sub_commands.append(('install_messages', has_messages))
    _install.sub_commands.append(('install_manpages', has_manpages))


### End of snippet ###


class install_manpages(Command):

    description = "Install man pages"

    user_options = []

    def initialize_options(self):
        self.man_pages = man_pages
        self.install_dir = None
        self.root = None

    def finalize_options(self):
        self.set_undefined_options(
            'install',
            ('install_data', 'install_dir'),
            ('root', 'root'),
        )

    def run(self):
        for f in self.man_pages:
            attrs = f.split(".")
            dest = os.path.join(self.install_dir, "share", "man")
            try:
                dest = os.path.join(dest, attrs[2])
            except IndexError:
                pass
            dest = os.path.join(dest, "man" + attrs[1])
            self.mkpath(dest)
            self.copy_file(f, dest)


man_pages = glob("man/*")

setup(name="elogv",
      version="0.7.9",
      author="Luca Marturana",
      author_email="lucamarturana@gmail.com",
      license="GPL-2",
      description="Curses based utility to view elogs created by Portage",
      url="https://gitweb.gentoo.org/proj/elogv.git/",
      scripts=['elogv'],
      cmdclass={
          'extract_messages': messages,
          'merge': merge,
          'build_messages': build_messages,
          'build': build,
          'install_messages': install_messages,
          'install_manpages': install_manpages,
          'install': install,
          'clean': clean
      })
