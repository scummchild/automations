"""
Wrapper classes for Paramiko SSH and SFTP clients.

"""
import getpass
import stat

import paramiko

class MySFTPClient(paramiko.SFTPClient):
    """The paramiko sftp client will error if the directory already exists,
    so subclassing to ignore that with an optional parameter"""

    def mkdir(self, path, mode=511, ignore_existing=False):
        """Augments mkdir by adding an option to not fail if the folder exists"""
        try:
            super(MySFTPClient, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise

class SSHServer():
    """Wrapper around the paramiko SSH client for little
    tweaks like prompting for passwords and printing out
    command outputs"""
    def __init__(self, hostname, username, password, key_file):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_file = key_file

        self.transport = paramiko.Transport(sock=f'{self.hostname}:22')
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if not self.key_file and not self.password:
            self.password = getpass.getpass()

        if self.password is None:
            k = paramiko.RSAKey.from_private_key_file(key_file)
            self.transport.connect(username=self.username, pkey=k)
            self.ssh.connect(hostname=self.hostname, username=self.username, pkey=k)
        else:
            self.transport.connect(username=self.username, password=self.password)
            self.ssh.connect(hostname=self.hostname, username=self.username, password=self.password)

        self.sftp = MySFTPClient.from_transport(self.transport)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.hostname}, {self.username}, {self.key_file})'

    def put_sh(self, localpath, remotepath):
        """Extends put by doing extra cleanup on executable files"""
        self.sftp.put(localpath=localpath, remotepath=remotepath)

        dos2ux_command = f'/usr/bin/dos2ux {remotepath} > {remotepath}_tmp; ' + \
            f'mv {remotepath}_tmp {remotepath}'
        self.execute(dos2ux_command)

        # cmhod the .sh to user r w x, group r, others r
        self.sftp.chmod(
            path=remotepath,
            mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IROTH)

    def execute(self, command):
        """Wraps Paramiko's exec_command with a print of outputs"""
        _stdin, stdout, stderr = self.ssh.exec_command(command)

        for line in stderr:
            print(line, end='')

        for line in stdout:
            print(line, end='')
