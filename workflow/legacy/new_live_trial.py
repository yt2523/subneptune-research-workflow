import datetime as dt, uuid
from workflow import BASE,Store
r=BASE/'runs'/('live-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]); s=Store(r)
s.initialize('Create profile.py using Python standard library only. Functions pressure_pa(p_bar) converts a positive finite numeric pressure in bar to Pa (1 bar=100000 Pa), raising ValueError for zero, negative or nonfinite inputs. validate(p_bar,t_kelvin) takes two lists of numbers, raises ValueError for different lengths, fewer than two levels, nonpositive or nonfinite entries, or non-strictly-increasing pressures; returns True otherwise. Do not model planetary physics, interpolate, or add I/O. This is a workflow utility test, not a physical TP model.')
print(r)
