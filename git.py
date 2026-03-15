import subprocess, dotbot, os, shlex

from pprint import PrettyPrinter

class DotbotGit(dotbot.Plugin):
    _directive = 'git'

    def can_handle(self, directive):
        return self._directive == directive

    def handle(self, directive, data):
        if directive != self._directive:
            raise ValueError('git cannot handle directive %s' %
                directive)

        success = True
        defaults = self._context.defaults().get('git', {})

        for clone_path in data:
            url = defaults.get('url')
            branch = defaults.get('branch')
            commit = defaults.get('commit')
            method = defaults.get('method')
            recursive = defaults.get('recursive')
            description = defaults.get('description')

            repo_definition = data[clone_path]

            if isinstance(repo_definition, dict):
                url = repo_definition.get('url', url)
                branch = repo_definition.get('branch', branch)
                commit = repo_definition.get('commit', commit)
                method = repo_definition.get('method', method)
                recursive = repo_definition.get('recursive', recursive)
                description = repo_definition.get('description', description)
            else:
                url = repo_definition

            repo = self.Repository(self._log)
            repo.path = os.path.abspath(os.path.expanduser(clone_path))

            if url is not None:
                repo.url = url
            else:
                success = False
                self._log.error('Failed to clone repository! (no url specified)')
                continue

            if branch is not None:
                repo.branch = branch

            if commit is not None:
                repo.commit = commit

            if method is not None:
                if method in ['clone', 'pull', 'clone-or-pull']:
                    repo.method = method
                else:
                    self._log.warning('Method ' + method + 'is not defined! (Will be ignored…)')

            if recursive is not None:
                repo.recursive = recursive

            if description is not None:
                repo.description = description
            
            if not repo.load():
                success = False

        return success

    class Repository:
        path=None
        url=None
        branch=None
        commit=None
        method='clone-or-pull'
        description=None
        recursive=False

        _log = None

        def __init__(self, _log):
            self._log = _log

        def load(self):
            method = None

            # check the load method to use
            if self.method == 'clone':
                method = 'clone'
            if self.method == 'pull':
                method = 'pull'
            if self.method == 'clone-or-pull':
                if self._repo_exists():
                    method = 'pull'
                else:
                    method = 'clone'

            # sanity checks
            if method == 'clone':
                if self._repo_exists():
                    method = None
                    self._log.lowinfo("Repository already exists! Won't clone " + self._get_description())
            if method == 'pull':
                if not self._repo_exists():
                    method = None
                    self._log.error("Repository doesn't exist! Won't pull " + self._get_description())

            # loading
            success = True
            if method == 'clone':
                success = self._clone()

                self._log.lowinfo('Cloned ' + self._get_description())
            elif method == 'pull':
                success = self._pull()

                self._log.lowinfo('Pulled ' + self._get_description())
            if self.branch is not None:
                current_branch = self._get_current_branch()
                if current_branch != self.branch:
                    self._checkout('branch')

            if self.commit is not None:
                current_commit = self._get_current_commit()
                if current_commit != self.commit:
                    self._checkout('commit')
            return success

        def _clone(self):
            if not os.path.isdir(self.path):
                os.makedirs(self.path)

            command = 'git clone --quiet '

            if self.recursive:
                command += '--recurse-submodules '

            command += self.url + ' "' + self.path + '"'

            return self._run_command(command)

        def _pull(self):
            command = 'git --work-tree="' + self.path + '"'
            command += ' --git-dir="' + self.path + '/.git"'
            command += ' pull --quiet'
            
            if self.recursive:
                command += ' --recurse-submodules '

            return self._run_command(command)

        def _checkout(self, source='branch'):
            if source == 'branch':
                if self.branch is None:
                    return True
                goto = self.branch
            if source == 'commit':
                if self.commit is None:
                    return True
                goto = self.commit

            command = 'git --work-tree="'+self.path+'"'
            command += ' --git-dir="'+self.path+'/.git"'
            command += ' checkout --quiet --force ' + goto

            return self._run_command(command)

        def _get_current_commit(self):
            p = subprocess.Popen(
                    shlex.split('git --git-dir="' + self.path + '/.git" rev-parse HEAD'),
                    shell=False,
                    stdout=subprocess.PIPE)
            output = p.communicate()[0].decode()
            if p.returncode == 0:
                return output.strip()
            return False

        def _get_current_branch(self):
            p = subprocess.Popen(
                    shlex.split('git --git-dir="' + self.path + '/.git" branch --show-current'),
                    shell=False,
                    stdout=subprocess.PIPE)
            output = p.communicate()[0].decode()
            if p.returncode == 0:
                return output.strip()
            return False

        def _run_command(self, command):
            try:
                subprocess.run(
                        shlex.split(command),
                        shell=False,
                        check=True)
                return True
            except subprocess.CalledProcessError:
                self._log.error('git command failed…')
                return False

        def _repo_exists(self):
            return os.path.isdir(os.path.join(self.path, '.git'))

        def _get_description(self):
            if self.description is None:
                return 'into ' + self.path
            else:
                return self.description
