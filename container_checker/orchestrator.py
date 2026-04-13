from concurrent.futures import ThreadPoolExecutor, as_completed

from .logging_utils import logger


def normalize_container_numbers(container_numbers):
    return [container.strip().upper() for container in container_numbers]


def check_terminal(checker, container_numbers):
    try:
        logger.info(f"Checking containers at {checker.terminal_name}")
        results = checker.check_containers(container_numbers)
        logger.info(f"Completed checking at {checker.terminal_name}")
        return results
    except Exception as exc:
        logger.error(f"Error checking containers at {checker.terminal_name}: {exc}")
        return []
    finally:
        if hasattr(checker, "driver") and checker.driver:
            checker.driver.quit()


def run_checks(checkers, container_numbers, parallel=False):
    container_results = {}

    if parallel:
        with ThreadPoolExecutor(max_workers=len(checkers)) as executor:
            future_to_checker = {executor.submit(check_terminal, checker, container_numbers): checker for checker in checkers}
            for future in as_completed(future_to_checker):
                checker = future_to_checker[future]
                try:
                    results = future.result()
                    for result in results:
                        container = result.container_number
                        if result.terminal != "NOT FOUND":
                            container_results[container] = [result]
                        elif container not in container_results:
                            container_results[container] = [result]
                except Exception as exc:
                    logger.error(f"Error checking containers at {checker.terminal_name}: {exc}")
        return container_results

    remaining_containers = container_numbers.copy()
    for checker in checkers:
        try:
            if not remaining_containers:
                break

            logger.info(f"Checking containers at {checker.terminal_name}")
            results = checker.check_containers(remaining_containers)

            new_remaining = remaining_containers.copy()
            for result in results:
                container = result.container_number
                if result.terminal != "NOT FOUND":
                    if container in new_remaining:
                        new_remaining.remove(container)
                    container_results[container] = [result]
                elif container not in container_results:
                    container_results[container] = [result]

            remaining_containers = new_remaining
            logger.info(f"Completed checking at {checker.terminal_name}")
            logger.info(f"Remaining containers: {remaining_containers}")
        except Exception as exc:
            logger.error(f"Error checking containers at {checker.terminal_name}: {exc}")
        finally:
            if hasattr(checker, "driver") and checker.driver:
                checker.driver.quit()

    return container_results
