import asyncio

from server import Server


def main():
    server = Server()
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
