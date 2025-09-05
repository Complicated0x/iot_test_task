import asyncio
import struct
import datetime
import logging
import json

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 9000

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def xor_sum(buffer) -> bytes:
    temp_sum = 0
    for byte in buffer:
        temp_sum ^= byte
    return temp_sum

def make_handshake(receiverId: bytes, senderId: bytes, data: bytes) -> bytes:
    """Authorization"""
    try:
        header = bytearray(b"@NTC")
            
        header += senderId
        header += receiverId
        
        if not isinstance(data, bytes):
            raise TypeError(f"Data must be bytes, got {type(data)}")
        
        size = len(data).to_bytes(2, "little")
        header += size
        
        try:
            checksum_data = xor_sum(data)
            header.append(checksum_data)
        except Exception as e:
            raise RuntimeError(f"Failed to calculate data checksum: {e}")
        
        header.append(0)
        try:
            checksum_header = xor_sum(header[:15])
            header[15] = checksum_header
        except Exception as e:
            raise RuntimeError(f"Failed to calculate header checksum {e}")
            
        return bytes(header) + data
    except Exception as e:
        logger.error(f"Handshake creation failed: {e}")

async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Server handler"""
    client = writer.get_extra_info('peername')
    logger.info(f"Новое подключение к серверу: {client}")
    try:
        data = await reader.read(100)
        if not data:
            logger.warning(f"Client {client} has disconnected")
            return
        idobj = data[4:8]
        iddc = data[8:12]
        if not b"S:" in data:
            logger.warning("Device id is missing")
        device_id = data.decode('ascii').split("S:")[1]
    except asyncio.IncompleteReadError:
        logger.warning(f"Client {client} terminated the connection")
    
    response = make_handshake(idobj, iddc, data=b"*<S")
    writer.write(response)
    logger.info("Handshake Good",)
    
    await writer.drain()
    try:
        await parse_device_data(reader, client, device_id)
    except Exception as e:
        logger.error(f"Error {e}")
        
async def parse_device_data(reader, client, device_id):
    try:
        while True:
            try:
                more_data = await reader.read(100)
                if not more_data:
                    logger.warning(f"Client {client} disconnected after handshake")
                    break
                unpacked_timestamp = struct.unpack('<I', more_data[8:12])[0]
                timestamp = datetime.datetime.fromtimestamp(unpacked_timestamp)
                
                latitude = struct.unpack('<I', more_data[20:24])[0]
                longitude = struct.unpack('<I', more_data[24:28])[0]
                speed = struct.unpack('<I', more_data[28:32])[0]
            except struct.error:
                logger.error(f"Client {client} sent broken data")
                break
            if datetime.datetime.now().year == timestamp.year:
                logger.info(pack_data(device_id, str(timestamp), latitude, longitude, speed))
    except Exception as e:
        logger.error(f"Error {e}")
        
def pack_data(device_id: int, timestamp: str, latitude: int, longitude: int, speed: int) -> str:
    data = {
        "device_id": device_id,
        "timestamp": timestamp,
        "latitude": latitude / 1000000,
        "longitude": longitude / 1000000,
        "speed": speed
        }
    return json.dumps(data, indent=4)
        
async def main():
    try:
        server = await asyncio.start_server(handle, SERVER_HOST, SERVER_PORT)
        async with server:
            await server.serve_forever()
    except OSError as e:
        logger.error(f"Network or port error: {e}")

asyncio.run(main())