"""StudyBox 运行入口。"""
from config import load_settings


def main():
    settings = load_settings()
    print(f"欢迎，{settings['course']}！")


if __name__ == "__main__":
    main()
