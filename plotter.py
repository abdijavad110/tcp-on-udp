from datetime import datetime
from matplotlib import pyplot as plt


txt = open('client_CWND_log.txt').read().split("\n")
txt = txt[:len(txt)-2]
start = datetime.strptime(txt[0].split()[1], '%H:%M:%S,%f:')
times = list(map(lambda q:(datetime.strptime(q.split()[1], '%H:%M:%S,%f:') - start).total_seconds(), txt))
sizes = list(map(lambda q: int(q.split()[6]), txt))
plt.plot(times, sizes)
plt.savefig('CWND.png')
