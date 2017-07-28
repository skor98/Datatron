import numpy as np
from collections import Counter

data = []

with open('bets_paths.txt', 'r', encoding='utf-8') as file:
    for line in file:
        data.append(int(line))

print('Количество элементов: {}'.format(len(data)))
print('Среднее: {}'.format(np.mean(data)))
print('Стандартное отклонени: {}'.format(np.std(data)))
print('Медиана: {}'.format(
    data[len(data) // 2 + 1]
    if len(data) % 2 != 0
    else (data[len(data) // 2 + 1] + data[len(data) // 2]) / 2
))
print('Мода: {}'.format(Counter(data)))
print('Мин: {}'.format(min(data)))
print('Макс: {}'.format(max(data)))
