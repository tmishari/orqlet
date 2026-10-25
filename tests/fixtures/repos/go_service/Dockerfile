# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM golang:1.25 AS builder
RUN go build ./...
FROM registry.example.com/team/chainguard-base:latest
FROM scratch
FROM ${BASE_IMAGE}
