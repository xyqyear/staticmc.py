from server import MCServer


def main():
    server_thread = MCServer()
    server_thread.start()
    server_thread.join()


if __name__ == "__main__":
    main()
