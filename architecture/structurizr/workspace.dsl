workspace {
    model {
        # See the MLOps Skill Profiles Whitepaper for definitions
        mleng = person "ML Engineer"
        ds = person "Data Scientist"
        cto = person "CTO / Management"
        it = person "IT / (Dev)Ops"
        
        infra = softwareSystem "Infrastructure Product" {
            executionEngine = container "Execution Engine" {
              jobSubmission = component "Job Submission" "Accepts jobs for scheduling and execution" {
              }
              jobMonitoring = component "Job Monitoring" "Monitors execution of jobs"
              jobExecution = component "Job Execution" "Executes jobs as local processes" {
                jobSubmission -> this "Executes local jobs"
              }
              imageBuilder = component "Image Builder" "Assembles container images from specification" {
                jobSubmission -> this "Builds container image for execution"
              }
            }

            auth = container "Authentication & Authorization Service"

            auditLog = container "Audit Log" "" "" "Database" {
              jobMonitoring -> this "Tracks modifications to jobs"
            }
        
            ds -> jobSubmission "Submits jobs" "CLI"
            executionEngine -> ds "Returns job results"
            ds -> infra "Monitors own jobs' statuses"
            ds -> infra "Troubleshoots failed jobs"
            ds -> infra "Terminates (own) pending/running jobs"

            mleng -> infra "Assign resources to individual jobs"
            mleng -> infra "Monitors a team's compute resource usage"

            it -> auth "Manages teams and permissions"
            it -> this "Assigns access permissions to teams"
            it -> this "Assigns resource quotas to teams"

            cto -> this "Assigns budgets to teams and performs accounting"
            cto -> this "Allocates usage quotas"

            # Thoughts:
            # - translating compute resource to budget usage / quotas
            # - get the project sheet template from IT

        }

        k8s = softwareSystem "Execution Platform" "" "external" {
          ray = container "Ray Operator" {
              jobSubmission -> this "Schedules jobs"
          }
          
          kueue = container "Kueue" {
              jobSubmission -> this "Schedules jobs"
          }
          executionEngine -> this "Monitors resources"
        }

        it -> k8s "Provisions"
        it -> k8s "Monitors resource usage and availability"
        
        notifier = softwareSystem "Notification Service" "" "external" {
            jobMonitoring -> this "Sends Notification Using"
            this -> ds "Notifies"
        }
    }

    views {
        systemContext infra {
          include *
          autolayout
        }
        container infra {
          include *
          autolayout
        }
        component executionEngine {
          include *
          autolayout
        }
        
        styles {
            element "external" {
                background #999999
            }
            element "Database" {
                shape Cylinder
            }
            element "Browser" {
                shape WebBrowser
            }
        }
        
        themes default "https://static.structurizr.com/themes/kubernetes-v0.3/theme.json"
    }
}
