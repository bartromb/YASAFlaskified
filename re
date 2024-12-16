sudo systemctl stop rq-worker@*
sudo systemctl start rq-worker@{1..2}
sudo systemctl start rq-worker@{1..2}
sudo systemctl restart nginx && sudo systemctl restart YASAFlaskified
