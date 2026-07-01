# ─── Application Load Balancer ───────────────────────────────────────────────

resource "aws_lb" "main" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "production"

  tags = { Name = "${var.app_name}-alb" }
}

# ─── Target Groups ────────────────────────────────────────────────────────────

resource "aws_lb_target_group" "backend" {
  name        = "${var.app_name}-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${var.app_name}-backend-tg" }
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.app_name}-frontend-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${var.app_name}-frontend-tg" }
}

# ─── Listeners ────────────────────────────────────────────────────────────────

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  # Redirect HTTP → HTTPS in production
  default_action {
    type = var.environment == "production" ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.environment == "production" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    dynamic "forward" {
      for_each = var.environment != "production" ? [1] : []
      content {
        target_group {
          arn = aws_lb_target_group.frontend.arn
        }
      }
    }
  }
}

# ─── Routing rules: /api/* → backend, everything else → frontend ──────────────

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  condition {
    path_pattern {
      values = ["/api/*", "/health", "/docs", "/openapi.json"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
