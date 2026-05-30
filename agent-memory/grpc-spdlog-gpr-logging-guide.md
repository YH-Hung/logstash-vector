# C++ gRPC gpr Logging With spdlog Guide

This guide is for the external C++ gRPC server repository. The gRPC server source is not part of this `logstash-vector` repo; this repo only needs the Vector side that reads the emitted log file and converts matching lines to Prometheus metrics.

## Goal

Configure gRPC Core (`gpr`) logging in a C++ gRPC server so logs are written through `spdlog` in the format consumed by the Vector gRPC metrics pipeline:

```text
I0530 12:34:56.123456   12345 server.cc:87] started grpc server
```

Required regex shape:

```regex
^(?<sev>[IWEF])(?<date>\d{4}) (?<time>\d{2}:\d{2}:\d{2}\.\d{6})\s+(?<tid>\d+) (?<file>[^:]+):(?<line>\d+)\] (?<msg>.*)$
```

## Important Notes

- Register the handler during server process initialization, before building or starting the gRPC server.
- Set the `spdlog` pattern to `%v`; the handler formats the complete target line itself.
- `gpr_log_severity` usually has `DEBUG`, `INFO`, and `ERROR`. The handler below maps `DEBUG` and `INFO` to `I`, and `ERROR` to `E`. The Vector regex also accepts `W` and `F` for compatibility with other log producers.
- `gpr_set_log_function` and `gpr_set_log_verbosity` are gRPC Core APIs and may change in newer gRPC releases. If the server uses a gRPC version that has fully moved to Abseil logging, use an Abseil `LogSink` instead.
- `args->file` comes from `__FILE__`. Most builds emit a bare basename (e.g. `server.cc`), which is what the Vector `file` metric label expects. Some build setups (e.g. Bazel, or CMake without relative source paths) emit a directory-prefixed path like `src/core/server.cc`. Because `file` becomes a Prometheus label, a path prefix would raise label cardinality. If your build emits prefixes, strip to the basename before formatting the line (e.g. take the substring after the last `/`).

## Example Implementation

Add a small logging setup module in the external gRPC server repository, for example `grpc_logging.cc`.

```cpp
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <functional>
#include <memory>
#include <string>
#include <thread>

#include <grpc/support/log.h>
#include <spdlog/fmt/fmt.h>
#include <spdlog/sinks/rotating_file_sink.h>
#include <spdlog/spdlog.h>

#if defined(__linux__)
#include <sys/syscall.h>
#include <unistd.h>
#endif

namespace {

std::shared_ptr<spdlog::logger> g_grpc_logger;

char SeverityChar(gpr_log_severity severity) {
  switch (severity) {
    case GPR_LOG_SEVERITY_ERROR:
      return 'E';
    case GPR_LOG_SEVERITY_INFO:
      return 'I';
    case GPR_LOG_SEVERITY_DEBUG:
      return 'I';
  }
  return 'I';
}

spdlog::level::level_enum SpdlogLevel(gpr_log_severity severity) {
  switch (severity) {
    case GPR_LOG_SEVERITY_ERROR:
      return spdlog::level::err;
    case GPR_LOG_SEVERITY_INFO:
      return spdlog::level::info;
    case GPR_LOG_SEVERITY_DEBUG:
      return spdlog::level::debug;
  }
  return spdlog::level::info;
}

long CurrentThreadIdForLog() {
#if defined(__linux__)
  return static_cast<long>(syscall(SYS_gettid));
#else
  return static_cast<long>(
      std::hash<std::thread::id>{}(std::this_thread::get_id()) & 0x7fffffff);
#endif
}

std::string FormatGrpcLogLine(const gpr_log_func_args* args) {
  using namespace std::chrono;

  const auto now = system_clock::now();
  const auto micros =
      duration_cast<microseconds>(now.time_since_epoch()) % seconds(1);
  const std::time_t now_time = system_clock::to_time_t(now);

  std::tm local_tm;
#if defined(_WIN32)
  localtime_s(&local_tm, &now_time);
#else
  localtime_r(&now_time, &local_tm);
#endif

  char date_time[32];
  std::strftime(date_time, sizeof(date_time), "%m%d %H:%M:%S", &local_tm);

  return fmt::format("{}{}.{:06d} {:7d} {}:{}] {}",
                     SeverityChar(args->severity),
                     date_time,
                     static_cast<int>(micros.count()),
                     CurrentThreadIdForLog(),
                     args->file,
                     args->line,
                     args->message);
}

void GrpcSpdlogHandler(gpr_log_func_args* args) {
  if (!g_grpc_logger) {
    return;
  }

  g_grpc_logger->log(SpdlogLevel(args->severity), "{}", FormatGrpcLogLine(args));
}

gpr_log_severity ParseGrpcVerbosity(const char* value) {
  if (value == nullptr) {
    return GPR_LOG_SEVERITY_INFO;
  }

  const std::string level(value);
  if (level == "DEBUG") {
    return GPR_LOG_SEVERITY_DEBUG;
  }
  if (level == "INFO") {
    return GPR_LOG_SEVERITY_INFO;
  }
  if (level == "ERROR") {
    return GPR_LOG_SEVERITY_ERROR;
  }

  return GPR_LOG_SEVERITY_INFO;
}

}  // namespace

void ConfigureGrpcLogging() {
  const char* path = std::getenv("GRPC_LOG_FILE");
  if (path == nullptr) {
    path = "/app/log/grpc_server.log";
  }

  g_grpc_logger = spdlog::rotating_logger_mt(
      "grpc-core",
      path,
      100 * 1024 * 1024,
      5);

  // The Vector parser expects the raw message only, without spdlog timestamps
  // or logger names. Format the full target line in GrpcSpdlogHandler().
  g_grpc_logger->set_pattern("%v");
  g_grpc_logger->set_level(spdlog::level::debug);
  g_grpc_logger->flush_on(spdlog::level::info);

  gpr_set_log_function(GrpcSpdlogHandler);
  gpr_set_log_verbosity(ParseGrpcVerbosity(std::getenv("GRPC_VERBOSITY")));
}
```

Call `ConfigureGrpcLogging()` from the external server startup code before creating or starting the gRPC server:

```cpp
int main(int argc, char** argv) {
  ConfigureGrpcLogging();

  grpc::ServerBuilder builder;
  // Existing server setup continues here.
}
```

## Runtime Configuration

Use environment variables to control output path and verbosity:

```bash
GRPC_LOG_FILE=/app/log/grpc_server.log GRPC_VERBOSITY=INFO ./grpc-server
GRPC_LOG_FILE=/app/log/grpc_server.log GRPC_VERBOSITY=DEBUG ./grpc-server
GRPC_LOG_FILE=/app/log/grpc_server.log GRPC_VERBOSITY=ERROR ./grpc-server
```

For gRPC Core tracing, set `GRPC_TRACE` separately:

```bash
GRPC_LOG_FILE=/app/log/grpc_server.log \
GRPC_VERBOSITY=DEBUG \
GRPC_TRACE=api,call_error \
./grpc-server
```

## Vector Contract

The Vector side should read files matching `/app/log/grpc_*.log` unless deployment chooses another path. If a different path is used, update `sources.grpc_log_files.include` in `impl/vector.yaml`.

The log line emitted by the handler must match this example exactly enough for the regex parser:

```text
I0530 12:34:56.123456   12345 server.cc:87] started grpc server
```

Avoid adding a normal spdlog prefix such as `[2026-05-30 12:34:56] [info]`, because that would prevent the Vector regex from matching.

## Verification

Run the external server and confirm the log file contains matching lines:

```bash
grep -E '^[IWEF][0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}[[:space:]]+[0-9]+ [^:]+:[0-9]+\] ' /app/log/grpc_server.log
```

Then confirm Vector exposes metrics:

```bash
curl -s http://localhost:9598/metrics | grep grpc_log_messages_total
```
