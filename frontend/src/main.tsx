import React from 'react';
import ReactDOM from 'react-dom/client';
import { App as AntApp, ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './style.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ConfigProvider locale={zhCN} theme={{ token: {
    colorPrimary: '#176b62', colorInfo: '#176b62', borderRadius: 8, fontSize: 14,
    fontFamily: 'Inter, "Segoe UI", "Microsoft YaHei", sans-serif', colorBgLayout: '#f5f6f8',
  } }}><AntApp><App /></AntApp></ConfigProvider></React.StrictMode>,
);
