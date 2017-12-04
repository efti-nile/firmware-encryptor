import sys


class ProgBar:
    WIDTH = 80

    def __init__(self, text=''):
        text_len = len(text)
        assert text_len < round(self.WIDTH * 0.8)
        beg = (self.WIDTH - text_len) // 2
        end = beg + text_len
        line = '|' + '-' * (beg - 1) + text + '-' * (self.WIDTH - end - 1) + '|\n'
        sys.stdout.write(line)
        self.num_of_bars = 0

    def update(self, prog):
        assert 0.0 <= prog <= 1.0
        num_bars_to_add = round(self.WIDTH * prog) - self.num_of_bars
        sys.stdout.write('|' * num_bars_to_add)
        sys.stdout.flush()
        self.num_of_bars += num_bars_to_add

    def close(self):
        sys.stdout.write('|' * (self.WIDTH - self.num_of_bars) + '\n')
        self.num_of_bars = self.WIDTH

if __name__ == '__main__':
    from time import sleep
    pb = ProgBar('Test bar')
    N = 10
    for i in range(N):
        pb.update(float(i)/N)
        sleep(0.5)
    pb.close()
    pb2 = ProgBar('Test bar number 2')
    for i in range(N - 3):
        pb2.update(i / N)
        sleep(0.1)
    pb2.close()
