class ReadQueries:
    def __init__(self, filepath):
        try:
            with open(filepath, encoding='utf-8-sig') as text_file:
                text_data = text_file.readlines()
        except UnicodeDecodeError:
            with open(filepath, encoding='cp1251') as text_file:
                text_data = text_file.readlines()

        self.queries = [t.rstrip('\n') for t in text_data]
