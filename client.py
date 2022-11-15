# This is client.py
from server import *
import hashlib

period = f""
USERNAME = ""

def _argparse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--ip", default='127.0.0.1', action='store', required=False, dest="ip",
                       help="The IP address bind to the server. Default bind to localhost.")
    parse.add_argument("--port", default='1379', action='store', required=False, dest="port",
                       help="The port that server listen on. Default is 1379.")
    parse.add_argument("--id", default='2033922', action='store', required=False, dest="id",
                       help="The id is the USERNAME in get_authorization. Default is 2033922.")
    parse.add_argument("--file", default='picture.jpg', action='store', required=False, dest="file",
                       help="The file that will be sent to server. Default is the picture.jpg")
    return parse.parse_args()


def get_authorization(clientSocket):
    """
    Send auth information and receive a TCP "packet" containning token
    :param clientSocket: the TCP clientSocket to send packet
    :return: Token
    """
    global USERNAME
    PASSWORD = hashlib.md5(USERNAME.encode()).hexdigest()

    # send auth information
    json_data = {
        FIELD_DIRECTION: DIR_REQUEST,
        FIELD_OPERATION: OP_LOGIN,
        FIELD_TYPE: TYPE_AUTH,
        FIELD_USERNAME: USERNAME,
        FIELD_PASSWORD: PASSWORD
    }
    packet = make_packet(json_data)
    clientSocket.send(packet)

    # receive packet from server side, judge the token exit and right or not
    received_json_data, received_bin_data = get_tcp_packet(clientSocket)
    if FIELD_TOKEN not in received_json_data:
        print("Fail to get FILED_TOKEN!")
        return received_json_data
    user_str = f'{json_data[FIELD_USERNAME].replace(".", "_")}.' \
               f'{get_time_based_filename("login")}'
    md5_auth_str = hashlib.md5(f'{user_str}kjh20)*(1'.encode()).hexdigest()
    if base64.b64encode(f'{user_str}.{md5_auth_str}'.encode()).decode() != received_json_data[FIELD_TOKEN]:
        print("Token is incorrect!")
        return received_json_data
    return received_json_data[FIELD_TOKEN]

def get_uploading_plan(clientSocket, token, size_file):
    """
    Get file uploading plan and get the key
    :param clientSocket:
    :param token:
    :param size_file:
    :return: key, file_size, block_size, total_block, and so on
    """
    # send uploading application
    json_data = {
        FIELD_DIRECTION: DIR_REQUEST,
        FIELD_OPERATION: OP_SAVE,
        FIELD_TYPE: TYPE_FILE,
        FIELD_TOKEN: token,
        FIELD_SIZE: size_file
    }
    packet = make_packet(json_data)
    clientSocket.send(packet)

    # receive packet from server side and jude the key exit or not
    received_json_data, received_bin_data = get_tcp_packet(clientSocket)
    if FIELD_KEY not in received_json_data:
        print("Fail to get FILED_KEY!")
        return False
    return received_json_data

def uploading_file(clientSocket, token, key_block, bin_data):
    """
    Keeping sending block_size_binary_file_data untill get file_MD5
    :param clientSocket:
    :param token:
    :param key_block: key, file_size, block_size, total_block and so on
    :param bin_data: the binary data of the uploading files
    :return: file_MD5
    """
    global period
    starttime = time.time()
    block_index = 0
    key = key_block[FIELD_KEY]
    size_file = key_block[FIELD_SIZE]
    block_size = key_block[FIELD_BLOCK_SIZE]
    total_block = key_block[FIELD_TOTAL_BLOCK]

    while True:
        json_data = {
            FIELD_DIRECTION: DIR_REQUEST,
            FIELD_OPERATION: OP_UPLOAD,
            FIELD_TYPE: TYPE_FILE,
            FIELD_TOKEN: token,
            FIELD_KEY: key,
            FIELD_BLOCK_INDEX: block_index
        }

        start_index = block_size * block_index
        end_index = start_index + block_size if block_index != total_block - 1 else size_file
        block_bin_data = bin_data[start_index:end_index]

        # send joson_data and the block binary data of file
        packet = make_packet(json_data, block_bin_data)
        clientSocket.send(packet)

        # receive packet from server and update block_index, key, check file_MD5 exists in packets
        received_json_data, received_bin_data = get_tcp_packet(clientSocket)
        block_index = received_json_data[FIELD_BLOCK_INDEX] + 1
        key = received_json_data[FIELD_KEY]
        if FIELD_MD5 in received_json_data:
            endtime = time.time()
            period = round(endtime - starttime, 4)
            return received_json_data[FIELD_MD5]

def main():
    global USERNAME
    parser = _argparse()
    server_ip = parser.ip
    server_port = parser.port
    USERNAME = parser.id
    file = parser.file
    server_IP_port = (server_ip, int(server_port))
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect(server_IP_port)

    # Firstly get token from server
    token = get_authorization(clientSocket) # string
    if isinstance(token,dict):
        return
    print(f"Right Token is {token}")

    fhand = open(file,'rb')
    bin_data = fhand.read()
    size_file = len(bin_data)

    # File uploading plan and get the key along with the requirements for files
    key_block = get_uploading_plan(clientSocket,token,size_file) # dict
    if key_block is False:
        return
    print(key_block)

    # File uploading block by block and get file_MD5
    file_MD5 = uploading_file(clientSocket, token, key_block, bin_data)
    print(f"File_MD5 is {file_MD5} \nPeriod for sending this file is {period} secs")

if __name__ == "__main__":
    main()
