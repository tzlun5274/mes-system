const mysql = require('mysql2');
const pool = mysql.createPool({
    host: 'mes-mysql',
    user: 'mes',
    password: 'ctech2015',
    database: 'mes',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

module.exports = pool.promise();