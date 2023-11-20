# Checker for SX service

## Requirements

- python 3.10 (at least)
- Faker (preferably 19.13.0 version)
- requests (preferably 2.31.0 version)

## Howto

```
usage: SX checker [-h] host {put,check} flag_id flag

positional arguments:
  host
  {put,check}
  flag_id
  flag

options:
  -h, --help   show this help message and exit
```

examples:
```bash
./checker.py 127.0.0.1 put "somekekeke" "6a331fd2-133a-4713-9587-12652d34666d12"
```

```bash
./checker.py 127.0.0.1 check "somekekeke" "6a331fd2-133a-4713-9587-12652d34666d12"
```