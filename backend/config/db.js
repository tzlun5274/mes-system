
const mysql = require('mysql');

const db = mysql.createConnection({
    host: 'localhost',
    user: 'mes',
    password: 'ctech2015',
    database: 'mes'
});

db.connect(err => {
    if (err) throw err;
    console.log('Connected to the database!');
});

module.exports = db;
