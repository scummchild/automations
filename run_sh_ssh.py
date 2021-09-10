"""This script tests a "runnin" .sh file that DBAs use to migrate Oracle code.
Using sftp, all the files mentioned in the .sh are copied to
the saturn server (in your home folder). Then ssh is used to execute the sh
and return the output.

Make sure that the desired target database is in the top of the sh
"""

import argparse
from pathlib import Path
import re
from SSHServer import SSHServer


def parse_script_arguments():
    """Setting up the arguments passed into this script from the command line"""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'sh',
        help='String of the absolute file path to the sh file')

    parser.add_argument(
        'username',
        help='The username to use when sshing into saturn')

    parser.add_argument(
        '--keyfile',
        help='String of the absolute file path to the key file to use when sshing into saturn',
        default=None)

    parser.add_argument(
        '--saveremote',
        help='When done running, leave any files still on ssh server.',
        action="store_true")

    return parser.parse_args()


def parse_sh(sh_file):
    """This helper function searches the sh file for sqlplus commands.
    The files that are called with sqlplus will be the ones sent to the server via sftp.

    This function yields a Path object

    """
    # Looking for lines like
    # sqlplus idb@$DBCUS @$DB_STATEFUL/function/BIL_RETRO_EXTRACT_FUNC.fnc < $SECURE/idb$DBCUS.sec
    # OR
    # sqlplus sot01@$DBOPS @PRDDDC-987_sot01_update_email.sql update < $SECURE/sot01$DBOPS.sec
    # OR
    # sqlplus rcs@$DBCUS @PRDSDWP-741_rcs_drop.sql < $SECURE/rcs$DBCUS.sec
    # The second grouping of parenthesis will catch the file path
    # (\s is whitespace, \S is non-whitespace)
    script_pattern = re.compile(r'sqlplus\s+(\S+)\s+(\S+).+')

    with open(sh_file) as sh:
        text = sh.read()

        for match in script_pattern.finditer(text):
            match_text = match.group(2).replace('@', '')
            match_list = match_text.split('/')

            if match_list[0] == '$DB_STATEFUL':
                # I'm assuming that the script is run from the deployment folder
                # so this variable finds the absolute path to the stateful folder.
                stateful_path = Path('').joinpath(
                    *sh_file.parts[0:sh_file.parts.index('deployment')] +
                    ('stateful', 'oracle_database'))
                match_path = stateful_path.joinpath(*match_list[1:])
            else:
                match_path = sh_file.parent.joinpath(match_list[0])

            yield match_path


def main():
    """Main driving function"""
    args = parse_script_arguments()
    sh_path = Path(args.sh)
    # This finds the lowest level directory, probably a string of the JIRA number
    parent_dir = sh_path.parts[-2]

    saturn = SSHServer(
        hostname='saturn.decare.com',
        username=args.username,
        password=None,
        key_file=args.keyfile)

    with saturn.sftp as sftp:
        with saturn.ssh:
            # prepare the top remote directory
            remote_sh_dir = f'/home/{args.username}/{parent_dir}/'
            remote_sh_file = f'{remote_sh_dir}{sh_path.name}'
            sftp.mkdir(remote_sh_dir, ignore_existing=True)
            saturn.put_sh(localpath=sh_path, remotepath=remote_sh_file)

            # Loop over files referenced in the .sh file and sftp.put
            for file in parse_sh(sh_path):

                # file.parts[-2] is the lowest directory, like function or type or package
                if file.parts[-2] != parent_dir:
                    sftp.mkdir(
                        f'{remote_sh_dir}{file.parts[-2]}', ignore_existing=True)
                    sftp.put(
                        localpath=file,
                        remotepath=f'{remote_sh_dir}{file.parts[-2]}/{file.parts[-1]}')
                else:
                    sftp.put(
                        localpath=file,
                        remotepath=f'{remote_sh_dir}{file.parts[-1]}')

            saturn.execute(f'cd {remote_sh_dir};{remote_sh_file}')

            # sftp.get the *.log files back to the local directory
            for sh_dir_file in sftp.listdir(path=remote_sh_dir):
                if r'.log' in sh_dir_file:
                    sftp.get(
                        localpath=sh_path.parent.joinpath(sh_dir_file),
                        remotepath=f'{remote_sh_dir}{sh_dir_file}')

            # Remove the remote directory
            if not args.saveremote:
                saturn.execute(f'rm -r {remote_sh_dir}')


if __name__ == "__main__":
    main()
