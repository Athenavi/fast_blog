// Command plugin-market-server 是 FastBlog 的**可自建插件市场服务端**。
//
// 它只做一件事：把 {PMS_DATA_DIR}/plugins/{slug}/{version}.zip 这些插件包
// 暴露成一组只读 HTTP 接口，供 FastBlog 实例（或任何兼容客户端）浏览、下载与检查更新。
//
// 接口契约见 ../API.md；本实现刻意只用标准库，编译出单个可执行文件即可部署。
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	log.SetFlags(log.LstdFlags)
	log.SetPrefix("[pms] ")

	cfg, err := LoadConfig()
	if err != nil {
		log.Fatalf("配置错误：%v", err)
	}

	ix := NewIndex(cfg.DataDir)
	if err := ix.Refresh(); err != nil {
		log.Printf("初次索引失败（将以空市场启动）：%v", err)
	}
	for _, warning := range ix.Warnings() {
		log.Printf("索引告警：%s", warning)
	}

	srv := &http.Server{
		Addr:              cfg.Listen,
		Handler:           NewAPI(cfg, ix),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf("%s v%s 启动于 %s（只读=%v，数据目录=%s，插件数=%d）",
			cfg.SiteName, cfg.Version, cfg.Listen, cfg.ReadOnly, cfg.DataDir, ix.Count())
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("监听失败：%v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("关闭时出错：%v", err)
	}
	ix.FlushChecksumCache()
	log.Print("已退出")
}
