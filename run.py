import argparse
from wms import WMS

def main():
    parser = argparse.ArgumentParser(description="query inventories, create inbound and outbound orders from RK WMS.")
    parser.add_argument('-q', '--query', action='store_true', help='query existing inventories')
    parser.add_argument('-p', '--product', type=str, help="Specify part number")
    parser.add_argument('-i', '--inbound', type=int, help='number of inbound receipts')
    parser.add_argument('-o', '--outbound', type=int, help='number of outbound orders')
    parser.add_argument('-c', '--containers', type=str, nargs='+', help='specify container numbers (e.g., -c container1 container2 container3)')
    parser.add_argument('-d', '--date', nargs='+', help="Specify outbound date")
    args = parser.parse_args()

    wms = WMS()
    try:
        # log in 
        wms.login()

        # query 
        if args.query:
            print("Querying RK inventories...")
            if wms.query_inventory():
                print("Export inventories to csv: SUCCEED")
            else:
                print(f"Invetory query failed: {str(e)}")
            if wms.upload_to_gdrive():
                print("Uploade to Gdrive: SUCCEED.")
            else:
                print("Uploade to Gdrive: FAILED.")


        # create inbound
        if args.inbound is not None:
            if args.containers:
                print("Creating inbound receipts...")
                for container in args.containers:
                    if wms.create_inbound(container, args.product, args.inbound):
                        print(f"container {container} receipt creation: SUCCESS.")
                    else:
                        print(f"container {container} receipt creation: FAILED.")
            else:
                print("Error: '-i' option requires '-c' option.")

        # create outbound
        if args.outbound is not None:
            if args.containers:
                print("Creating outbound orders...")
                for i in range(len(args.containers)):
                    if wms.create_outbound(args.containers[i], args.product, args.date[i], args.outbound):
                        print(f"container {args.containers[i]} order creation: SUCCESS.")
                    else:
                        print(f"container {args.containers[i]} order creation: FAILED.")
            else:
                print("Error: '-o' option requires '-c' option.")

    except Exception as e:
        print("Error:", e)

    wms.driver.quit()

if __name__ == "__main__":
    main()
