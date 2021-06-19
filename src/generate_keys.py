import os


def create_server_key():
    os.system(
        '''openssl req -new -x509 -days 365 -nodes -out server.pem -keyout server.key -subj "/C=PL/ST=Lublin/L=Lublin/O=PAS-Snake/OU=IT Department/CN=SNAKE" ''')


def create_client_key():
    os.system(
        '''openssl req -new -x509 -days 365 -nodes -out client.pem -keyout client.key -subj "/C=PL/ST=Lublin/L=Lublin/O=PAS-Snake/OU=IT Department/CN=SNAKE" ''')


if __name__ == "__main__":
    print("Generate keys...")
    create_server_key()
    create_client_key()
    print("Done.")
