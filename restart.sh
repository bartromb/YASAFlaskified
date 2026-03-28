# 1. Stop host Nginx permanent
sudo systemctl stop nginx
sudo systemctl disable nginx

# 2. Clean start
cd ~/YASAFlaskifiedv71
docker compose down
docker compose up -d

# 3. Check
docker compose ps
curl -s -o /dev/null -w "%{http_code}" http://localhost/login
